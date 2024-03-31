import sys
import os
from flask import Flask, request, jsonify,render_template
from agent import chat_agent
from utils import ChatScanUtils,ChatTimeLogUtils,ApiUtils
from news_mongo import mongo_utils
from common import ActionEnum,PresetEnum,ChatQuestionEnum
from order import parse_order 
from job import job
from service import news_service,alert_service,itb_service
import logging
import traceback
import time
import datetime
from werkzeug.utils import cached_property
import logging
app = Flask(__name__)

APP_ENV=os.getenv("APP_ENV")
CLIENT_TOKEN=os.getenv("CLIENT_TOKEN")

logging.basicConfig(filename='../log/news_chat.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
app = Flask(__name__)

class ReturnT:
    @staticmethod
    def success(data):
        return jsonify({"code": 200, "msg": "success", "data": data})

    @staticmethod
    def fail(msg="internal server error",code=500):
        return jsonify({"code": code, "msg": msg, "data": None})



def validate_token(token):
    client_tokens = CLIENT_TOKEN.split(",")
    # Replace 'your_secret_token' with the actual secret token you're expecting
    return token in client_tokens

@app.route('/getChatList', methods=['GET'])
def get_chat_list():
    try:
        token = request.headers.get('Authorization')
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
                                
        user_id = request.args.get('userId')
        if user_id:
            chat_list = news_service.getAiChatList(user_id)
            logging.info(chat_list)
            return ReturnT.success(chat_list)
        return ReturnT.fail("userId error")
    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail()           

@app.route("/createChat", methods=["POST"])
def createChat():
    try:
        token = request.headers.get('Authorization')
        # Validate the token
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        client = token.split("_")[0]+APP_ENV
        logging.info(client)
        chat_data = request.get_json()
        logging.info(chat_data)
        user_id = chat_data.get("userId")
        aiChat = news_service.createAiChat(client,user_id)
      
        return ReturnT.success(aiChat)
    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail("internal server error")  

@app.route("/feedback", methods=["POST"])
def feedback():
    try:
        token = request.headers.get('Authorization')
        # Validate the token
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        chat_question = request.get_json()
        logging.info(chat_question)
        result = news_service.feedback(chat_question)
        return ReturnT.success(result)
    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail("internal server error")  

@app.route('/getQuestionList', methods=['GET'])
def getQuestionList():
    try:
        token = request.headers.get('Authorization')
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        
        userId = request.args.get('userId')
        chatId = request.args.get('chatId')
        if userId and chatId:
            chat_list = news_service.getLastedQuestion(userId,chatId,100)
            return ReturnT.success(chat_list)
        else:
            return ReturnT.fail("userId or chatId error")
    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail("internal server error")  



@app.route("/onchain/token/list", methods=['GET'])
def onchain_tokenlist_route():
    try:
        start_time = time.time()
        token = request.headers.get('Authorization')
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        else:
            request_arg = request.args.get('token_ids')
            logging.info(request_arg)
            result = itb_service.find_itb_token_list()
            end_time = time.time()
            logging.info("chat run time %s",(end_time - start_time))
            return ReturnT.success(result)
    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail('internal server error')

@app.route("/onchain/token/summary", methods=['POST'])
def onchain_tokensummary_route():
    try:
        start_time = time.time()
        token = request.headers.get('Authorization')
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        else:
            request_data = request.get_json()
            logging.info(request_data)
            token_ids = request_data.get("token_ids")
            print(type(token_ids))
            print(token_ids)
            result = itb_service.find_itb_summary_by_token_id(token_ids)
            end_time = time.time()
            logging.info("onchain summary run time %s",(end_time - start_time))
            return ReturnT.success(result)
    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail('internal server error')


@app.route("/preset", methods=["POST"])
def preset():
    try:
        start_time = time.time()
        token = request.headers.get('Authorization')
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        client = token.split("_")[0]

        chat_data = request.get_json()
        
        userId = chat_data.get("userId")
        chatId = chat_data.get("chatId")
        question = chat_data.get("question")
        canSave = chat_data.get("canSave")
        longModel = chat_data.get("longModel")
        presetType = chat_data.get("presetType")
        input_tokens = chat_data.get("tokens")
        
        logging.info("chat question %s",question)

        if not userId or not chatId:
            logging.info(f"userId {userId} or chatId {chatId} has no text ")
            return ReturnT.fail("params error")
    
        chat_question = news_service.ChatQuestion(client,userId, chatId)
        
        if longModel == True:
            logging.info("long model")
            chat_question.longModel = True
        
        chat_question.question = question
        chat_question.canSave = canSave
        timeLogs = []
        logging.info("presetType %s",presetType)
        subTimeLogs = []
        tokens = []
        chat_result = None
        if input_tokens and len(input_tokens) > 0:
            for t in input_tokens:
                tokens.append(t.lower())
        if presetType == PresetEnum.PresetType.METRICS.value:
            if len(tokens) > 0:
                chat_result,subTimeLogs = chat_agent.preset_metrics(chat_question,tokens)
        elif presetType == PresetEnum.PresetType.GPT.value :     
            chat_result,subTimeLogs = chat_agent.preset_knowlage(chat_question)
        elif presetType == PresetEnum.PresetType.NEWS.value:
            if len(tokens) > 0:
                chat_result,subTimeLogs = chat_agent.preset_news(chat_question,tokens)
        elif presetType == PresetEnum.PresetType.POSTS.value:
            if len(tokens) > 0:
                chat_result,subTimeLogs = chat_agent.preset_posts(chat_question,tokens)
        elif presetType == PresetEnum.PresetType.FEAR_INDEX.value:
            chat_result,subTimeLogs = chat_agent.preset_index(chat_question)
        elif presetType == PresetEnum.PresetType.DIGEST.value:
            if len(tokens) > 0:
                chat_result,subTimeLogs = chat_agent.preset_digest(chat_question,tokens)
        if chat_result is None:
            chat_result,subTimeLogs = chat_agent.preset_search_knowlage(chat_question)

        chat_question.answerType = chat_result.type
        answer = chat_result.answer
        chat_question.chatAnswer = chat_result.chat_answer
        chat_question.compliance = chat_result.compliance
        chat_question.links = chat_result.links.split("\n") if chat_result.links else []

        lasted_question_list = mongo_utils.get_lasted_question(
            chat_question.userId,chat_question.chatId,1
        )
        round_id = 0
        if lasted_question_list:
            lasted_question = lasted_question_list[0]
            if lasted_question is None:
                raise Exception("BusinessException: 400000")
            round_id = lasted_question["round"] or 0

        round_id += 1
        chat_question.round = round_id

        try:
            now = datetime.datetime.now()
            chat_question.createDate = now
            chat_question.updateDate = now
            str_answer = str(answer)
            chat_question.answer = str_answer
            mongo_utils.insert_data("chat_question",chat_question.__dict__)
        except Exception as e:
            print(f"save chatQuestion error {chat_question} {e}")
        chat_question.answer = chat_result.answer
        end_time = time.time()
        usedTime= "{:.2f}".format(end_time - start_time)
        logging.info("preset chat run time %s",usedTime)

        try:
            chatUsedTimeLog = ChatTimeLogUtils.ChatTimeSubLog(ActionEnum.ChatAction.PRESET_CHAT.value,usedTime)
            timeLogs.append(chatUsedTimeLog)
            timeLogs.extend(subTimeLogs)
            chat_question.timeLogs = timeLogs
            chatTimeLog = ChatTimeLogUtils.ChatTimeLog(client,APP_ENV,userId,chatId,question)
            chatTimeLog.createDate = datetime.datetime.now()
            chatTimeLog.roundId = chat_question.round
            chatTimeLog.timeLog = timeLogs
            ChatTimeLogUtils.saveChatTimeLog(chatTimeLog)
        except Exception as e:
            exc_info = traceback.format_exception(*sys.exc_info())
            logging.error("chat log ".join(exc_info))      

        return ReturnT.success(chat_question.__json__())

    except Exception as e:
        logging.error(str(e))
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail("internal server error")

@app.route("/metrics", methods=["POST"])
def metrics():
    try:
        start_time = time.time()
        token = request.headers.get('Authorization')
        # Validate the token
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        chat_data = request.get_json()
        logging.info(chat_data)
        token_ids = chat_data.get("token_ids")
        result = news_service.find_metrics_by_token_id(token_ids)
        end_time = time.time()
        logging.info("chat run time %s",(end_time - start_time))
        return ReturnT.success(result)

    except Exception as e:
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail("internal server error")
    


@app.route("/defed/chat", methods=["POST"])
def defed_chat():
    try:
        start_time = time.time()
        token = request.headers.get('Authorization')
        # Validate the token
        if not validate_token(token):
            return ReturnT.fail("authentication failed",401)
        client = token.split("_")[0]

        chat_data = request.get_json()
        
        userId = chat_data.get("userId")
        chatId = chat_data.get("chatId")
        roundId = chat_data.get("roundId")
        question = chat_data.get("question")
        questionType = chat_data.get("questionType")
        canSave = chat_data.get("canSave")
        longModel = chat_data.get("longModel")

        logging.info("defed-chat question %s",question)
        if not userId or not chatId:
            logging.info(f"userId {userId} or chatId {chatId} has no text ")
            return ReturnT.fail("params error")
        
        timeLogs = []
        chat_question = news_service.ChatQuestion(client,userId, chatId)
        if longModel == True:
            logging.info("long model")
            chat_question.longModel = True
        chat_question.question = question
        chat_question.canSave = canSave
        chat_question.round = roundId
        chat_result,subTimeLogs = news_service.defed_chat(chat_question,questionType)
        end_time = time.time()
        usedTime= "{:.2f}".format(end_time - start_time)
        try:
            chatUsedTimeLog = ChatTimeLogUtils.ChatTimeSubLog(ActionEnum.ChatAction.CHAT.value,usedTime)
            timeLogs.append(chatUsedTimeLog)
            timeLogs.extend(subTimeLogs)
            chat_question.timeLogs = timeLogs
            chatTimeLog = ChatTimeLogUtils.ChatTimeLog(client,APP_ENV,userId,chatId,question)
            chatTimeLog.createDate = datetime.datetime.now()
            chatTimeLog.roundId = chat_question.round
            chatTimeLog.timeLog = timeLogs
            ChatTimeLogUtils.saveChatTimeLog(chatTimeLog)
        except Exception as e:
            exc_info = traceback.format_exception(*sys.exc_info())
            logging.error("chat log ".join(exc_info))      

        return ReturnT.success(chat_result.__json__())

    except Exception as e:
        logging.error(str(e))
        exc_info = traceback.format_exception(*sys.exc_info())
        logging.error("".join(exc_info))
        return ReturnT.fail("internal server error")


initFlag = False
def init():
    global initFlag
    if not initFlag:
        logging.info("%s aichat app start",APP_ENV)
        mongo_utils.initDBPool()
        chat_agent.init()
        # parse_order.init()
        ApiUtils.init()
        
        job.start_job1()
        logging.info("aichat app end")
        initFlag = True

if __name__ == '__main__':
    logging.info("aichat app start")
    init()
    # job.start_job1()
    app.run(host='0.0.0.0', port=5002,debug=False)

