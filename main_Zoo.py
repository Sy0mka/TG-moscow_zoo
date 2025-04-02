import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    ApplicationBuilder
)
from quiz_data import questions, results
from utils_Zoo import calculate_result
from config_Zoo import TOKEN, ADMIN_CONTACT_EMAIL, ADMIN_CONTACT_PHONE, SOCIAL_MEDIA_LINKS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
QUESTION, RESULT = range(2)


async def start(update: Update, context: CallbackContext) -> int:
    """Начало викторины"""
    context.user_data.clear()
    context.user_data['answers'] = {}
    context.user_data['current_question'] = 0

    await update.message.reply_text(
        "🦁 Добро пожаловать в викторину Московского зоопарка!\n"
        "Ответьте на несколько вопросов, чтобы узнать свое тотемное животное!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Начать викторину!", callback_data="start_quiz")]
        ])
    )
    return QUESTION


async def show_question(update: Update, context: CallbackContext) -> int:
    """Показ текущего вопроса"""
    query = update.callback_query
    await query.answer()

    current = context.user_data['current_question']
    if current >= len(questions):
        return await show_result(update, context)

    question = questions[current]
    keyboard = [
        [InlineKeyboardButton(option, callback_data=str(i))]
        for i, option in enumerate(question["options"])
    ]

    try:
        await query.edit_message_text(
            text=f"Вопрос {current + 1}/{len(questions)}\n\n{question['question']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Вопрос {current + 1}/{len(questions)}\n\n{question['question']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return QUESTION


async def handle_answer(update: Update, context: CallbackContext) -> int:
    """Обработка ответа"""
    query = update.callback_query
    await query.answer()

    current = context.user_data['current_question']
    answer_idx = int(query.data)

    # Сохраняем ответ
    context.user_data['answers'][questions[current]["key"]] = questions[current]["options"][answer_idx]
    context.user_data['current_question'] += 1

    return await show_question(update, context)


async def show_result(update: Update, context: CallbackContext) -> int:
    """Показ результата с изображением"""
    result_key = calculate_result(context.user_data['answers'])
    result = results.get(result_key, results["equal"])

    # Отправка изображения
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=open(result['image'], 'rb'),
            caption=f"🎉 {result['text']}\n\n"
                    "Хотите узнать больше о программе опеки над животными?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Узнать об опеке", callback_data="about"),
                    InlineKeyboardButton("Поделиться", callback_data="share")
                ],
                [InlineKeyboardButton("Пройти ещё раз", callback_data="restart")]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке изображения: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎉 {result['text']}\n\n"
                 "Хотите узнать больше о программе опеки над животными?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Узнать об опеке", callback_data="about"),
                    InlineKeyboardButton("Поделиться", callback_data="share")
                ],
                [InlineKeyboardButton("Пройти ещё раз", callback_data="restart")]
            ])
        )

    return RESULT


async def about_program(update: Update, _: CallbackContext) -> None:
    """Информация о программе опеки"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"🐾 Программа опеки над животными:\n\n"
        "Станьте опекуном выбранного животного и поддерживайте работу зоопарка!\n"
        f"Подробности: {SOCIAL_MEDIA_LINKS['VK']}\n\n"
        f"Контакты для связи:\n"
        f"📧 {ADMIN_CONTACT_EMAIL}\n"
        f"📱 {ADMIN_CONTACT_PHONE}",
        disable_web_page_preview=True
    )


async def share_result(update: Update, _: CallbackContext) -> None:
    """Поделиться результатом"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 Поделитесь своим результатом:\n\n"
        "Я прошел викторину Московского зоопарка и мое тотемное животное - ...!\n"
        "Попробуй и ты: @MoscowZooBot\n"
        f"{SOCIAL_MEDIA_LINKS['instagram']}"
    )


async def restart(update: Update, context: CallbackContext) -> int:
    """Перезапуск викторины"""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    return await start(update, context)


async def contact_admin(update: Update, _: CallbackContext) -> None:
    """Обработчик команды /contact"""
    await update.message.reply_text(
        f"📬 Контакты Московского зоопарка:\n"
        f"Email: {ADMIN_CONTACT_EMAIL}\n"
        f"Телефон: {ADMIN_CONTACT_PHONE}\n\n"
        f"Мы в соцсетях:\n"
        f"VK: {SOCIAL_MEDIA_LINKS['VK']}\n"
        f"Instagram: {SOCIAL_MEDIA_LINKS['instagram']}",
        disable_web_page_preview=True
    )


async def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTION: [CallbackQueryHandler(handle_answer)],
            RESULT: [
                CallbackQueryHandler(about_program, pattern='^about$'),
                CallbackQueryHandler(share_result, pattern='^share$'),
                CallbackQueryHandler(restart, pattern='^restart$')
            ]
        },
        fallbacks=[CommandHandler('contact', contact_admin)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
