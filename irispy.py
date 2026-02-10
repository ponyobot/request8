from iris import ChatContext, Bot
from iris.bot.models import ErrorContext
from bots.cover_letter import handle_cover_letter

from iris.decorators import *
from iris.kakaolink import IrisLink

import sys, threading

iris_url = sys.argv[1]
bot = Bot(iris_url)

@bot.on_event("message")
def on_message(chat: ChatContext):
    try:
        if chat.room.id != 18473892252723619:
            return
        # 먼저 모든 메시지에서 자소서 처리 (명령어, 템플릿 저장 모두 포함)
        handle_cover_letter(chat)
        
        match chat.message.command:
            
            case "!명령어":
                chat.reply(f"{chat.room.name}의 명령어{ALLSEE}\n\n"
                           "자소서 명령어\n"
                           "────────────────\n"
                           "오픈채팅봇 명령어중 /3 하면 자소서가 나오는데 자소서 보내면 자동저장됩니다.\n"
                           "!자소서 - 자신의 자소서를 보여줍니다\n"
                           "!자소서 @멘션 - 멘션한 유저의 자소서를 보여줍니다\n"
                           "!자소서삭제 - 자신의 자소서를 삭제합니다"
                )

    except Exception as e :
        print(e)

@bot.on_event("error")
def on_error(err: ErrorContext):
    print(err.event, "이벤트에서 오류가 발생했습니다", err.exception)
    #sys.stdout.flush()

if __name__ == "__main__":
    #카카오링크를 사용하지 않는 경우 주석처리
    kl = IrisLink(bot.iris_url)
    bot.run()