# aws lambdaに設定するpythonコード。
# lineから送ったメッセージをchatGPTに投げて、chatGPTからの応答をレスポンスとして返す。
# 会話の履歴を考慮している。
#
# リクエストが来るたびに以下の動作をする。
# ・これまでの会話履歴をS3から取得
# ・LINEから受け取った新規メッセージとあわせてChatGPT APIに送信
# ・ChatGPT APIのレスポンスを取得
# ・LINEから受け取った新規メッセージとChatGPT APIのレスポンスを会話履歴に書き込み
# ・LINE Messaging APIにレスポンスを返却
#
# ついでに、
# ・listと送信するとこれまでの会話履歴を閲覧する
# ・clearと送信するとこれまでの会話履歴を削除
# する機能を追加。

import json
import os
import urllib.request
import openai
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

openai.api_key = os.environ['CHATGPT_API_KEY']
LINE_CHANNEL_ACCESS_TOKEN   = os.environ['LINE_CHANNEL_ACCESS_TOKEN']

BUCKET_NAME = 'alphajinsei-bucket'
OBJECT_KEY_NAME = 'chatGPT_messages.json'

s3 = boto3.resource('s3')

REQUEST_URL = 'https://api.line.me/v2/bot/message/reply'
REQUEST_METHOD = 'POST'
REQUEST_HEADERS = {
    'Authorization': 'Bearer ' + LINE_CHANNEL_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}


def lambda_handler(event, context):
    # リクエストの内容をログに出力
    logger.info("event")
    logger.info(event)
    
    logger.info("event_body")
    logger.info(event['body'])
    
    logger.info("recieved_text")
    logger.info(json.loads(event['body'])['events'][0]['message']['text'])
    
    
    # LINEから入力されたメッセージを取得
    recieved_text = json.loads(event['body'])['events'][0]['message']['text']
    
    # 会話履歴の呼び出し
    bucket = s3.Bucket(BUCKET_NAME)
    obj = bucket.Object(OBJECT_KEY_NAME)
    response = obj.get()    
    body = response['Body'].read()
    body_json = json.loads(body)
    
    logger.info("body_json")
    logger.info(type(body_json))
    logger.info(body_json)
    
    # リスト一覧取得の場合
    if recieved_text == 'list':
        # レスポンスの組み立て    
        REQUEST_MESSAGE = [
            {
                'type': 'text',
                'text': str(body_json) 
            }
        ]
    
    # 会話履歴を削除する場合
    elif recieved_text == 'clear':
        # 会話履歴を初期化
        body_json =  [{"role": "system", "content": "あなたは有能なアシスタントです"}]
        obj.put(Body=json.dumps(body_json)) 
        
        # list再取得
        response = obj.get()    
        body = response['Body'].read()
        body_json = json.loads(body)
        
        # レスポンスの組み立て    
        REQUEST_MESSAGE = [
            {
                'type': 'text',
                'text': str(body_json) 
            }
        ]
    
    # 会話を継続する場合    
    else: 
        # 会話履歴にLINEから入力されたメッセージを追加
        body_json.append({"role": "user", "content": recieved_text})
    
        
        # chat GPT呼び出し
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ChatGPT APIを使用するには'gpt-3.5-turbo'などを指定
            messages = body_json
            #messages=[
            #    {"role": "system", "content": "あなたは有能なアシスタントです"},
            #    {"role": "user", "content": recieved_text},
            #]
        )
        
        logger.info("ChatGPT result")
        logger.info(completion)
        answer_from_chatGPT = completion["choices"][0]["message"]["content"]
        
        #  会話履歴にChatGPTからの返答を追加
        body_json.append({"role": "system", "content": answer_from_chatGPT})
        
        # 会話履歴を書き込み
        obj.put(Body=json.dumps(body_json)) 
        
    
        # レスポンスの組み立て    
        REQUEST_MESSAGE = [
            {
                'type': 'text',
                'text': answer_from_chatGPT
            }
        ]
        
    # レスポンスの送信
    params = {
        'replyToken': json.loads(event['body'])['events'][0]['replyToken'],
        'messages': REQUEST_MESSAGE
    }
        
    request = urllib.request.Request(
        REQUEST_URL, 
        json.dumps(params).encode('utf-8'), 
        method=REQUEST_METHOD, 
        headers=REQUEST_HEADERS
        )
    response = urllib.request.urlopen(request, timeout=60)
    return 0