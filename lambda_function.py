# aws lambdaに設定するpythonコード。
# lineから送ったメッセージをchatGPTに投げて、chatGPTからの応答をレスポンスとして返す。
# 会話の履歴を考慮することは無く、単発のやり取りである点に注意。

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

    
    # chat GPT呼び出し
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # ChatGPT APIを使用するには'gpt-3.5-turbo'などを指定
        messages=[
            {"role": "system", "content": "あなたは有能なアシスタントです"},
            {"role": "user", "content": recieved_text},
        ]
    )
    
    logger.info("ChatGPT result")
    logger.info(completion)
    answer_from_chatGPT = completion["choices"][0]["message"]["content"]
    

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