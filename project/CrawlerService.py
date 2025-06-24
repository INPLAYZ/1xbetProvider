import AppSettings
from datetime import datetime, timedelta
import time
import os
import threading
from queue import Queue
import json
import random

class CrawlerService(object):
    def __init__(self, service_inputs):
        self.kafka_producers = service_inputs["kafka_producers"]
        self.machine_name = service_inputs["machine_name"]
        self.environment = service_inputs["environment"]
        self.version = service_inputs["version"]
        self.send_msg = service_inputs["send_msg"]
        self.provider = service_inputs["provider"]
        self.heart_txt = service_inputs["heart_txt"]
        self.topic = service_inputs["topic"]
        self.second_topic = service_inputs["second_topic"]
        self.setting = AppSettings.settings["service"]
        self.page_info = {"pregame": 0, "inplay": 0}
        self.start_time = time.time()
        self.pregame_queue = Queue()
        self.inplay_queue = Queue()
        self.lang_queue = Queue()
        self.send_kafka_queue = Queue()
        self.lang_dynamic_cooldown = 15
        self.pregame_dynamic_cooldown = 0.25
        threading.Thread(target=self.listen_status, args=()).start()
        threading.Thread(target=self.call_dashboard, args=()).start()
        threading.Thread(target=self.check_running_6H, args=()).start()

    def main(self):
        for _ in range(2):
            threading.Thread(target=self.get_pregame_gamedata).start()
        for _ in range(4):
            threading.Thread(target=self.get_inplay_gamedata).start()
        for _ in range(4):
            threading.Thread(target=self.get_lang_gamedata).start()
        threading.Thread(target=self.pregame_service).start()
        threading.Thread(target=self.inplay_service).start()
        threading.Thread(target=self.dynamic_cooldown_controller).start()
        threading.Thread(target=self.send_kafka).start()


    def pregame_service(self):
        need_lang_time = 0
        while True:
            try:
                need_lang = False
                self.page_info["pregame"] = 0
                league_id_list = self.get_pregame_league_id_list()
                #3小時抓一次lang data
                if time.time() - need_lang_time >= 10800:
                    need_lang = True
                    need_lang_time = time.time()
                for league_id in league_id_list:
                    threading.Thread(target=self.get_pregame_CI_code, args=(need_lang, league_id)).start()
                    time.sleep(0.5)
            except:
                self.send_msg()
            #因為sleep有點久，在provider同時版本更新後會有同時抓完同時sleep的情況 ->一段時間會沒資料，所以sleeptime改隨機
            time.sleep(random.randint(1500, 2200))

    def inplay_service(self):
        league_id_list = []
        last_get_list_time = time.time()
        while True:
            try:
                if not league_id_list or time.time() - last_get_list_time >= 60:
                    league_id_list = self.get_inplay_league_id_list()
                    last_get_list_time = time.time()
                for league_id in league_id_list:
                    threading.Thread(target=self.get_inplay_I_code, args=(league_id,)).start()
                    time.sleep(0.3)
            except:
                self.send_msg()

            time.sleep(70)

    def get_pregame_league_id_list(self):
        """
        獲取pregame所有聯盟的ID

        Returns:
            list: league_id_list
        """
        league_id_list = []
        try:
            # 取出字典中的值並進行排序(沒排序直接拿去call api會跳406)
            need_sports_values = sorted(self.setting["need_sports_pregame"].values(), key=int)
            game_type_list = ','.join(need_sports_values)
            game_type_api_result = self.provider.requests_data(f"https://1xbet.com/LineFeed/GetSportsShortZip?sports={game_type_list}&lng=en&tf=2200000&tz=8&country=179&virtualSports=true&gr=70&groupChamps=true", format="json()")
            if not game_type_api_result: return []
            for game_type_item in game_type_api_result["Value"]:
                if "L" not in game_type_item: continue #不是API對應的球種就不會有聯盟
                game_type = game_type_item["N"]
                if game_type not in ['Basketball', 'Baseball']: #除了BK、BS，其他球種2/3的機率跳過這次抓取
                    skip = random.choices([True, False], weights=[2, 1], k=1)[0]
                    if skip: continue
                for league_item in game_type_item["L"]:
                    if not self.check_ignore_league(game_type, league_item["L"]): continue #檢查不需要的聯盟
                    if "SC" not in league_item:
                        league_id_list.append(league_item["LI"])
                        continue
                    for SC_league in league_item["SC"]:
                        league_id_list.append(SC_league["LI"])
            random.shuffle(league_id_list) #打亂順序(不要每次都從足球開始call)
            return league_id_list
        except:
            self.send_msg()
            return []

    def get_inplay_league_id_list(self):
        """
        獲取inplay所有聯盟的ID

        Returns:
            list: league_id_list
        """
        league_id_list = []
        try:
            for game_type, game_type_id in self.setting["need_sports_inplay"].items():
                league_data = self.provider.requests_data(f"https://1xbet.com/LiveFeed/GetChampsZip?sport={game_type_id}&lng=en&gr=70&country=179&virtualSports=true&groupChamps=true", format="json()")
                if not league_data: continue
                if not league_data["Value"]: continue #該球種現在沒有inplay比賽
                for league_item in league_data["Value"]:
                    if not self.check_ignore_league(game_type, league_item["L"]): continue #檢查不需要的聯盟
                    if "SC" not in league_item:
                        league_id_list.append(league_item["LI"])
                        continue
                    for SC_league in league_item["SC"]:
                        league_id_list.append(SC_league["LI"])
            return league_id_list
        except:
            self.send_msg()
            return []

    def check_ignore_league(self, game_type, league_name) ->bool:
        if any(keyword in league_name for keyword in self.setting["ignore_league"]["all"]): return False
        if game_type == "Ice Hockey":
            if any(keyword in league_name for keyword in self.setting["ignore_league"]["Ice Hockey"]): return False
        if game_type == "Baseball":
            if any(keyword in league_name for keyword in self.setting["ignore_league"]["Baseball"]): return False
        #沒有在忽略名單內就返回true
        return True

    def get_pregame_CI_code(self, need_lang, league_id):
        """
        call 聯盟API，拿到該聯盟底下的所有比賽(比賽為簡易資訊)，獲取比賽的CI的值，然後丟到queue

        Args:
            need_lang (bool): 是否需要抓多語言
            league_id (int): league_id
        """
        league_detail = self.provider.requests_data(f"https://1xbet.com/LineFeed/GetChampZip?champ={league_id}&tz=8&tf=2200000&lng=en&country=179&gr=70", format="json()")
        if not league_detail or not league_detail["Value"]: return
        game_type = league_detail["Value"]["SN"]
        for game_info in league_detail["Value"]["G"]:
            game_timestamp = game_info["S"]
            game_timestamp = datetime.fromtimestamp(game_timestamp)
            current_time = datetime.now()
            if current_time.weekday() in [5, 6]: # 5代表星期六，6代表星期日
                if game_timestamp - current_time > timedelta(days=2): continue #假日大於2天的不抓(比賽太多)
            else:
                if game_timestamp - current_time > timedelta(days=3): continue #平日大於3天的不抓
            if game_info["O1"] == "Home" and game_info["O2"] == "Away": continue #不抓的賽事(主客隊為home/away)
            self.page_info["pregame"] += 1
            #比賽主要資訊的CI(常規時間)
            self.pregame_queue.put({"CI":game_info["CI"], "game_type":game_type})
            if need_lang:
                self.lang_queue.put({"CI":game_info["CI"], "game_type":game_type})
            #比賽次要資訊的CI(其他玩法)
            if game_type not in self.setting["need_odd_playmode"]: continue
            for odd_data in game_info.get("SG",[]):
                pn = odd_data["PN"]
                tg = odd_data.get("TG", "")
                play_mode = f"{pn} {tg}".strip()
                if play_mode not in self.setting["need_odd_playmode"][game_type]: continue
                self.pregame_queue.put({"CI":odd_data["CI"], "game_type":game_type})

    def get_inplay_I_code(self, league_id):
        try:
            league_detail = self.provider.requests_data(f"https://1xbet.com/LiveFeed/GetChampZip?champ={league_id}&lng=en&gr=70&country=179", format="json()")
            if not league_detail or not league_detail["Value"]: return
            game_type = league_detail["Value"]["SN"]
            for game_info in league_detail["Value"]["G"]:
                self.page_info["inplay"] += 1
                #比賽主要資訊的I(常規時間)
                self.inplay_queue.put({"I":game_info["I"], "game_type":game_type})
                #比賽次要資訊的I(其他玩法)
                if game_type not in self.setting["need_odd_playmode"]: continue
                for odd_data in game_info.get("SG",[]):
                    pn = odd_data["PN"]
                    tg = odd_data.get("TG", "")
                    play_mode = f"{pn} {tg}".strip()
                    if play_mode not in self.setting["need_odd_playmode"][game_type]: continue
                    self.inplay_queue.put({"I":odd_data["I"], "game_type":game_type})
        except:
            self.send_msg(f"league detail:{league_detail}")

    def get_pregame_gamedata(self):
        while True:
            try:
                CI_data = self.pregame_queue.get()
                game_id = CI_data["CI"]
                game_type = CI_data["game_type"]
                game_url = f"https://1xbet.com/LineFeed/GetGameZip?id={game_id}&lng=en&cfview=4&isSubGames=true&GroupEvents=true&allEventsGroupSubGames=true&countevents=2000&country=179&fcountry=179&marketType=1&gr=70&isNewBuilder=true"
                game_data = self.provider.requests_data(game_url, format="json()")
                if game_data and game_data["Success"] == True:
                    self.send_data(page_type="single", data=game_data, game_type=game_type, game_url=game_url)
            except:
                self.send_msg()
            time.sleep(self.pregame_dynamic_cooldown)

    def get_inplay_gamedata(self):
        while True:
            try:
                I_data = self.inplay_queue.get()
                game_id = I_data["I"]
                game_type = I_data["game_type"]
                game_url = f"https://1xbet.com/LiveFeed/GetGameZip?id={game_id}&lng=en&cfview=4&isSubGames=true&GroupEvents=true&allEventsGroupSubGames=true&countevents=2000&country=179&fcountry=179&marketType=1&gr=70&isNewBuilder=true"
                game_data = self.provider.requests_data(game_url, format="json()")
                if game_data and game_data["Success"] == True:
                    self.send_data(page_type="rbsingle", data=game_data, game_type=game_type, game_url=game_url)
            except:
                self.send_msg()
            time.sleep(0.2)

    def get_lang_gamedata(self):
        while True:
            try:
                CI_data = self.lang_queue.get()
                game_id = CI_data["CI"]
                game_type = CI_data["game_type"]
                lang_game_data = None
                for lang, site_lang in self.setting["need_lang"].items():
                    lang_game_data = self.provider.requests_data(f"https://1xbet.com/LineFeed/GetGameZip?id={game_id}&lng={site_lang}&cfview=4&isSubGames=true&GroupEvents=true&allEventsGroupSubGames=true&countevents=250&country=179&fcountry=179&marketType=1&gr=70&isNewBuilder=true", format="json()")
                    if lang_game_data and lang_game_data["Success"] == True:
                        simple_lang_data = {"Value":[
                            {
                                "S": lang_game_data["Value"].get("S", ""),
                                "EC": lang_game_data["Value"].get("EC", ""),
                                "League": lang_game_data["Value"].get("L", ""),
                                "O1": lang_game_data["Value"].get("O1", ""),
                                "O2": lang_game_data["Value"].get("O2", ""),
                                "LE": lang_game_data["Value"].get("LE", ""),
                                "O1E": lang_game_data["Value"].get("O1E", ""),
                                "O2E": lang_game_data["Value"].get("O2E", ""),
                                "LI": str(lang_game_data["Value"].get("LI", "")),
                                "O1I": str(lang_game_data["Value"].get("O1I", "")),
                                "O2I": str(lang_game_data["Value"].get("O2I", "")),
                                "SE": lang_game_data["Value"].get("SE", ""),
                                "SI": lang_game_data["Value"].get("SI", "")
                            }
                            ]
                        }
                        self.send_data(page_type=lang, data=simple_lang_data, game_type=game_type)
                    time.sleep(self.lang_dynamic_cooldown)
            except:
                self.send_msg(f"lang data:{lang_game_data}")
            time.sleep(self.lang_dynamic_cooldown)

    def dynamic_cooldown_controller(self):
        """
        根據queue的比賽數量動態調整請求速度(主要是調抓lang data的延遲)

        """
        while True:
            try:
                check_speed = 0
                if self.pregame_queue.qsize() == 0:
                    check_speed += 1
                self.lang_dynamic_cooldown = self.setting["dynamic_cooldown"]["lang"][str(check_speed)]
                check_speed = 0
                if self.pregame_queue.qsize() >= 4500:
                    check_speed += 1
                self.pregame_dynamic_cooldown = self.setting["dynamic_cooldown"]["pregame"][str(check_speed)]
                time.sleep(1)
            except:
                self.send_msg()

    def send_data(self, page_type, data, game_type, game_url=""):
        """送出資料到Game Data

        Args:
            page_type (str): 賽事狀態
            data (Dict[str, Any]): 賽事資料
            game_url (str): 網址
        """
        try:
            data['page_type'] = page_type
            data['timestamp'] = int(datetime.now().timestamp() * 1000),
            data['machinename'] = self.machine_name
            data['url'] = game_url
            if isinstance(data["Value"], list):
                data_P_value = 0 #list = 語系資料
            else:
                data_P_value = data.get('Value', -1).get('P', -1)
            data['p'] = data_P_value

            self.send_kafka_queue.put((game_type, data))
            #print(Datetime.Now(), page_type, lang, str(data)[:50])
        except:
            self.send_msg(msg=page_type)

    def send_kafka(self):
        SC_list = []
        not_SC_list = []
        need_send_time = time.time()
        while True:
            try:
                game_type, data = self.send_kafka_queue.get()
                if game_type == "Football":
                    SC_list.append(data)
                else:
                    not_SC_list.append(data)
                #每秒送一次
                if time.time() - need_send_time >= 1:
                    if len(SC_list) >= 1:
                        for kafka in self.kafka_producers:
                            kafka.send(self.second_topic, json.dumps(SC_list))
                        SC_list = []
                    if len(not_SC_list) >= 1:
                        for kafka in self.kafka_producers:
                            kafka.send(self.topic, json.dumps(not_SC_list))
                        not_SC_list = []
                    need_send_time = time.time()
            except:
                self.send_msg()

    def listen_status(self):
        while True:
            try:
                with open(self.heart_txt, 'r') as f:
                    status = f.read()
                if status == "0":
                    msg = "Control close program."
                    self.send_msg(msg=msg, level="Information")
                    os._exit(0)
                time.sleep(5)
            except:
                self.send_msg()
                time.sleep(5)
                continue


    def check_running_6H(self):
        while True:
            now = time.time()
            if self.start_time != "":
                if (now-self.start_time) > 21600: #6H = 21600
                    msg = "Running 6H, close program."
                    self.send_msg(msg=msg, level="Information")
                    os._exit(0)
            time.sleep(5)

    def call_dashboard(self):
        need_send = 0
        while True:
            try:
                dashboard_msg = f"pregame:{self.page_info['pregame']},inplay:{self.page_info['inplay']}"
                print(dashboard_msg)
                need_send += 1
                if need_send == 10:
                    msg = f"{datetime.now()} program alive, version is {self.version}, requests count: {self.provider.requests_count}, dashboard_msg: {dashboard_msg}"
                    self.send_msg(msg=msg, level="Information")
                    need_send = 0
                if self.provider.requests_status529_count >= 1:
                    self.send_msg(f"call api status 529 failed:{self.provider.requests_status529_count/self.provider.requests_count*100:.2f}%", level="Trace")
                print(f"pregame queue:{self.pregame_queue.qsize()}")
                print(f"inplay queue:{self.inplay_queue.qsize()}")
                print(f"lang queue:{self.lang_queue.qsize()}")
                self.provider.requests_count = 0
                self.provider.requests_status529_count = 0
                self.page_info["inplay"] = 0
            except:
                self.send_msg()
            time.sleep(60)