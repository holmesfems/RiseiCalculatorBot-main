アステシアちゃんbot
====
## Description
F鯖用、アークナイツプレイに役立つツールを持つ便利なDiscord botです

現在実装している機能：
* 理性価値表(/riseicalculator,/riseimaterials,/riseistages,/riseievents,/riseilists, /riseikakin)
* 公開求人検索(/recruitsim,/recruitlist)
* オペレーター育成の消費素材を調べる機能(/operetor○○cost)
* オペレーターの誕生日をお祝いする機能！！
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
* CLOUDVISION_API_KEY google cloud visionのAPIキー 公開求人のスクショ認識用

5. メインアプリを起動
```
python RiseiCalculator.py
```

## Install On Heroku
Herokuなどのサービス(有料)を使えば、リモートサーバーに本botを実行させることができるので、いつでも使えるようになります。
詳しくは[こちら](https://devcenter.heroku.com/ja/articles/github-integration)の公式記事を参照し、本リポジトリと連携して自動Deploy環境を構築してください

## ChangedLog
2023/11/05 
* 公開求人スクショOCR検索、大陸版のスクショを入れた場合のみ、大陸版の公開求人データから計算するようにしました（大陸版とグローバル版では一部の確定タグが異なります）
  ※パネル選択方式(/recruitsim)は、グローバル版のみの対応となります
* 確定タグ計算(/recruitlist)を大陸版に対応しました
* 確定タグ計算にポジションタグ(近距離、遠距離)を反映していなかった不具合を修正しました

2023/10/26
* グロ版参照のデータソースを最新データに対応したものに変更しました。
  イネス組の日本語版データが正しく反映されるようになります
  
2023/10/18 占い館から理性bot機能を呼び出せるように改修

2023/10/14 モジュールの消費素材を調べる機能を追加(/operatormodulecosts)

2023/10/04 公開求人にスクショ認識機能を追加

2023/09/10 riseimaterials,riseievents,riseistagesのコマンドに、excel出力機能を追加。表示したステージのドロップ率を出力します。

## Licence
Copyright (c) 2023 holmesfems

Released under MIT license

(http://opensource.org/licenses/mit-license.php)

## Author

[holmesfems](https://github.com/holmesfems)