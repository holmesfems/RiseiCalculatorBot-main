アステシアちゃんbot
====
## Description
F鯖用、アークナイツプレイに役立つツールを持つ便利なDiscord botです

現在実装している機能：
* 理性価値表(/riseicalculator,/riseimaterials,/riseistages,/riseievents,/riseilists)
* 公開求人検索(/recruitsim,/recruitlist)
* オペレーターの誕生日をお祝い！！
* chat-gptの会話機能

## Requirement
* python 3.11.3
* discord.py
* pandas
* scipy
* requests
* pyyaml
* openai
* openpyxl
* StrEnum

## Usage
Discordの鯖にbotを導入後、スラッシュコマンドにて実行可能

## Install On Local
1. [Discord Developer Portal](https://discord.com/developers/applications)から、Discordのbotアカウントを作り、bot IDのトークンを発行。
詳しくは[こちら](https://discordpy.readthedocs.io/ja/latest/discord.html)の公式記事を参照してください
Botアカウント発行の参考記事：[https://cod-sushi.com/discord-py-token/](https://cod-sushi.com/discord-py-token/)

2. ローカルから実行する場合、まずは本レポジトリをローカルにcloneします
```
git clone https://github.com/holmesfems/RiseiCalculatorBot-main.git
```

3. 必要パッケージをpipでインストール
```
python -m pip install -r ./requirements.txt
```

4. 実行に必要な環境変数をセットします
* BOT_ID botのAPPLICATION ID
* BOT_TOKEN botのトークン
* CHANNEL_ID_HAPPYBIRTHDAY オペレーター誕生日のお祝いに使うチャンネルのID
* OPENAI_API_KEY chat-gpt会話用、openaiアカウントのAPIキー
* OPENAI_CHANNELID chat-gpt会話用、会話を受け付けるチャンネルのID

5. メインアプリを起動
```
python RiseiCalculator.py
```

## Install On Heroku
Herokuなどのサービス(有料)を使えば、リモートサーバーに本botを実行させることができるので、いつでも使えるようになります。
詳しくは[こちら](https://devcenter.heroku.com/ja/articles/github-integration)の公式記事を参照し、本リポジトリと連携して自動Deploy環境を構築してください

## Licence
Copyright (c) 2023 holmesfems

Released under MIT license

(http://opensource.org/licenses/mit-license.php)

## Author

[holmesfems](https://github.com/holmesfems)