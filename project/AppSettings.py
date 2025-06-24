project_name = f"1xbetProvider"
topic = "test01"
second_topic = "test02"#足球寫到這個topic
heart = f'C:\Heart\heartOXBV2.txt'
#kafka集群
kafka_9 = []
kafka_10 = []
kafka_11 = []
environment_path = {
    "Local":{
        "send_html_data": [kafka_9]
    },
    "PRD":{
        "send_html_data": [kafka_9]
    },
    "PRD2":{
        "send_html_data": [kafka_10]
    },
    "PRD3":{
        "send_html_data": [kafka_11]
    },
}

settings = {
    "service":{
        "price_center_api":{
            "dashboard":"",
        },
        "need_sports_pregame":{
            "Football":"1",
            "Basketball":"3",
            "Baseball":"5",
            "American Football":"13",
            "Ice Hockey":"2",
            "Esports":"40",
            "Tennis":"4",
            "Volleyball":"6",
            "Boxing":"9",
            "Martial Arts":"56",
            "Snooker":"30",
            "Cricket":"66",
            "Darts":"21",
            "Badminton":"16",
            "Handball":"8",
            "Water Polo":"17",
            "Table Tennis":"10",
            "Kun Khmer": "275",
            "Muay Thai": "182",
            "UFC": "189"
        },
        "need_sports_inplay":{
            "Football":"1",
            "Basketball":"3",
            "Baseball":"5",
            "American Football":"13",
            "Ice Hockey":"2",
        },
        "ignore_league":{
            "all":[
                "5x5", "3x3", "3х3", "6x6", "Short Football", "2K21.", "2K20.", "Cyber League", "Cyber Euroleague"
                , "Table Basketball", "Table Soccer League","FIFA 21. ", "2x2","ACL Indoor","KLASK","Cyber PRO"
                ,"Soap Soccer League","4х4","4x4","Cyber NBA","REGBALL","eSports Battle","H2H GG League","Statistics Round"
                ,"eSports Battle","Soccer Box 2x2","MLB The Show","Space League","Esoccer","Alternative Matches","FIFA 22.","FIFA 23.","FIFA. LigaPro"
                ,"PRO League","Student League","NBA Cyber","NBA 2K22","2K23. NBA","Subsoccer","2K22. Euroleague","MLS+","NBA 2K23.","2K24."
            ],
            "Ice Hockey":[
                "Alternative Matches", "Cyber NHL 21", "3HL", "5HL", "NHL 20", "NHL 21", "NHL 22","Dream League"
                ,"3х3","Air Hockey League", "Grand tour", "Ice Cup", "NHL 23. Cyber"
            ],
            "Baseball":["Friendlies","NCAA"]
        },
        "need_lang": {
            "ja-JP": "ja",
            "ko-KR": "ko",
            "zh-CN": "cn",
            "zh-TW": "tw",
            "vi-VN": "vi",
            "th-TH": "th",
            "es-ES": "es",
            "fr-FR": "fr",
            "de-DE": "de",
            "pt-PT": "pt"
        },
        "dynamic_cooldown":{
            "lang":{
                "0":15,
                "1":0.2,
            },
            "pregame":{
                "0":0.25,
                "1":0.2,
            },
        },
        "need_odd_playmode": {
            "Baseball": [
                "1 Inning",
                "1-3 Inning",
                "1-5 Inning",
                "1-7 Inning",
                "2 Inning",
                "3 Inning",
                "4 Inning",
                "5 Inning",
                "6 Inning",
                "7 Inning",
                "8 Inning",
                "9 Inning"
            ],
            "Basketball": [
                "1 Quarter",
                "2 Quarter",
                "3 Quarter",
                "4 Quarter",
                "1 Half",
                "2 Half",
                "Assists",
                "Rebounds",
                "Three-Point Field Goals Scored"
            ],
            "Football": [
                "1 Half",
                "2 Half",
                "2 Half Yellow Cards",
                "Corners",
                "1 Half Corners",
                "2 Half Corners",
                "Cards",
                "Cards. Stats",
                "Yellow Cards",
                "1 Half Yellow Cards",
            ],
            "American Football": [
                "1 Quarter",
                "2 Quarter",
                "3 Quarter",
                "4 Quarter",
                "1 Half"
            ],
            "Ice Hockey": [
                "1 Period",
                "2 Period",
                "3 Period"
            ],
            "Esports": [
                "1 map",
                "2 map",
                "3 map",
                "4 map",
                "5 map"
            ],
            "Tennis": [
                "1 Set",
                "2 Set"
            ],
            "Volleyball": [
                "1 Set",
                "2 Set"
            ],
            "Handball":[
                "1 Half",
                "2 Half"
            ],
            "Badminton":[
                "1 Set",
                "2 Set"
            ],
            "Table Tennis":[
                "1 Set",
                "2 Set"
            ],
        }
    },
    "transformer":{},
}
