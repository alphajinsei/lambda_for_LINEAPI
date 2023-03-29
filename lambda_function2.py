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

s3_client = boto3.client('s3')

REQUEST_URL = 'https://api.line.me/v2/bot/message/reply'
REQUEST_METHOD = 'POST'
REQUEST_HEADERS = {
    'Authorization': 'Bearer ' + LINE_CHANNEL_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}


def logging_request(event):

    logger.info("event")
    logger.info(event)
    
    logger.info("event_body")
    logger.info(event['body'])
    
    logger.info("recieved_text")
    logger.info(json.loads(event['body'])['events'][0]['message']['text'])

    logger.info("userId")
    logger.info(json.loads(event['body'])['events'][0]['source']['userId'])



def lambda_handler(event, context):

    # リクエストの内容をログに出力
    logging_request(event)
    
    # LINEから入力されたメッセージを取得
    recieved_text = json.loads(event['body'])['events'][0]['message']['text']

    # 送信元のLINEユーザIDを取得
    userId = json.loads(event['body'])['events'][0]['source']['userId']

    # 個人の会話履歴ファイル名を設定
    OBJECT_KEY_NAME = 'chatGPT_messages_' + userId + '.json'

    # 会話履歴を呼び出してresponseに格納
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_NAME)
    
    # 会話履歴が存在しない場合、新規に作成したうえでresponseに内容を格納（新規ユーザを想定）
    except s3_client.exceptions.NoSuchKey as e:
        logger.info(e)
        conversation_history =  [{"role": "system", "content": "あなたは有能なアシスタントです"}]
        s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_NAME, Body=json.dumps(conversation_history)) 
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_NAME)

    # 会話履歴の内容を内部処理用に成形
    body = response['Body'].read()
    conversation_history = json.loads(body)
    
    logger.info("conversation_history")
    logger.info(type(conversation_history))
    logger.info(conversation_history)
    
    # リスト一覧取得の場合
    if recieved_text == 'list':
        # レスポンスの組み立て    
        REQUEST_MESSAGE = [
            {
                'type': 'text',
                'text': str(conversation_history) 
            }
        ]
    
    # 会話履歴を削除する場合
    elif recieved_text == 'clear':
        # 会話履歴を初期化
        conversation_history =  [{"role": "system", "content": "あなたは有能なアシスタントです"}]
        s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_NAME, Body=json.dumps(conversation_history)) 
        
        # list再取得
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_NAME)
        body = response['Body'].read()
        conversation_history = json.loads(body)
        
        # レスポンスの組み立て    
        REQUEST_MESSAGE = [
            {
                'type': 'text',
                'text': str(conversation_history) 
            }
        ]
    
    # 会話を継続する場合    
    else: 
        # 会話履歴にLINEから入力されたメッセージを追加
        conversation_history.append({"role": "user", "content": recieved_text})
    
        
        # chat GPT呼び出し
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ChatGPT APIを使用するには'gpt-3.5-turbo'などを指定
            messages = conversation_history
            #messages=[
            #    {"role": "system", "content": "あなたは有能なアシスタントです"},
            #    {"role": "user", "content": recieved_text},
            #]
        )
        
        logger.info("ChatGPT result")
        logger.info(completion)
        answer_from_chatGPT = completion["choices"][0]["message"]["content"]
        
        #  会話履歴にChatGPTからの返答を追加
        conversation_history.append({"role": "system", "content": answer_from_chatGPT})
        
        # 会話履歴を書き込み
        s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_NAME, Body=json.dumps(conversation_history)) 
        
    
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