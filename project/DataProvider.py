import requests
import os
import urllib3

class DataProvider(object):
    def __init__(self, send_msg):
        self.send_msg = send_msg
        self.session = None
        self.error_count = 0
        self.requests_count = 0
        self.requests_status529_count = 0
        urllib3.disable_warnings() #關閉SSL驗證警告


    def requests_data(self, url, method="get", format="text", post_data=[]):
        try:
            resp_data = ""
            status_code = ""
            session = self.get_session()
            if method == "get":
                respone = session.get(url, timeout = 60, verify=False) #verify=False = 移除SSL驗證
            else:
                if post_data:
                    respone = session.post(url, json=post_data, timeout = 5)
                else:
                    respone = session.post(url, timeout = 60)
            self.requests_count += 1
            status_code = respone.status_code
            resp_data = eval(f"respone.{format}")
            if status_code in [200, 204]:
                self.error_count = 0
            else:
                raise
            return resp_data
        except requests.exceptions.ConnectionError:
            #通常是SSL握手錯誤或者是VM的VPN斷線(除非錯誤太多否則不打log)
            self.error_count += 1
            if self.error_count >= 50:
                os._exit(0)
            self.close_session()
            if self.error_count >= 48:
                msg = f"url: {url}, method: {method} , format: {format}, post_data: {post_data}, status_code: {status_code}, error_count:{self.error_count}"
                self.send_msg(msg=msg, level="Warning")
            return ""
        except:
            self.error_count += 1
            if self.error_count >= 50:
                os._exit(0)
            self.close_session()
            #狀態529不打log
            if status_code == 529:
                self.requests_status529_count += 1
                return ""
            msg = f"url: {url}, method: {method} , format: {format}, post_data: {post_data}, status_code: {status_code}, error_count:{self.error_count}"
            self.send_msg(msg=msg, level="Warning")
            return ""


    def get_session(self):
        if self.session is None:
            self.session = requests.Session()
        return self.session


    def close_session(self):
        if self.session is not None:
            self.session.close()
            self.session = None
