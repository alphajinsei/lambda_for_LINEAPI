# lambda_for_LINEAPI

詳細は下記
https://qiita.com/alphajinsei/items/22cfbbefcbb00c0db30b

* 会話の履歴は(能動的に見ようと思えば)見えてしまうのであしからず
* 会話の履歴は30回(15往復)復前まで覚えていてくれます、30回を過ぎたものは古いものから忘れます
* 「list」と送信するとこれまでの会話履歴を見れます
* 「clear」と送信するとこれまでの会話を全て忘れます
* 1分以上返信がなかったら、「clear」を一回挟んでみてください(過去履歴含む会話の長さ制限に引っかかっている可能性が高い)

![./ChatGPT_through_LINE_MessagingAPI.png](./ChatGPT_through_LINE_MessagingAPI.png)

LINE Messaging APIから受けたリクエストを、
ChatGPT API (正確にはOpenAI APIの)に渡すAWS lambdaのコード。

スマホのLINEアプリ
→ LINE Messaging API
→ AWS API Gateway
→ AWS lambda
→ OpenAI ChatGPT
の構成。

環境変数に下記の設定が必要
* `CHATGPT_API_KEY` : OpenAIのAPIキー
* `LINE_CHANNEL_ACCESS_TOKEN` : LINE Messaging APIのキー
