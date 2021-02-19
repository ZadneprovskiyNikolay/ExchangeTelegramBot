from rates import Rates
from utils import get_last_work_day

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
from pandas.tseries.offsets import BDay
import pandas as pd
import matplotlib.pyplot as plt

import logging
import os
import sys
from datetime import date, datetime, timedelta
from functools import wraps
import re

logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger(__name__)

rates = Rates(caching_period_minutes=10)

def timed_rates_update(func):  
    """Декоратор обновляющий кеш котировок"""
    @wraps(func)
    def _wrapped(*args, **kwargs): 
        global rates            
        rates.update_rates_cache()
        return func(*args, **kwargs)
    return _wrapped

def get_rates(): 
    """Возвращает форматированный список котировок"""
    res = ''
    for currency, rate in rates.items():
        res += f'{currency}: {rate:.2f}\n'

    return res

@timed_rates_update
def list_rates(update, context):
    """Отвечает на команду /list: возвращает список последних котировок"""
    update.message.reply_text(get_rates())

@timed_rates_update
def exchange(update, context):    
    """Отвечает на команду '/exchange {cur1} to {cur2}' курсом 
    первой указанной валюты ко второй"""
    global rates_cache

    amount, cur1, cur2 = context.args[0], context.args[1].upper(), \
        context.args[3].upper()    

    # Проверяем аргументы запроса 
    try: 
        amount = float(amount)
        print(f'amount={amount}')
    except: 
        update.message.reply_text('Invalid amount for exchange.')
        return            
    if not rates.valid_currency(cur1): 
        update.message.reply_text(f'Invalid currency: {cur1}')
        return    
    if not rates.valid_currency(cur2): 
        update.message.reply_text(f'Invalid currency: {cur2}')
        return    

    # Формируем результат
    res_num = amount *  rates[cur2] / rates[cur1]
    res = f'{res_num:.2f} {cur2}'
    update.message.reply_text(res)

@timed_rates_update
def history(update, context):     
    cur_pair, days = context.args[0], context.args[2]
    match = re.match(r'(.*)/(.*)', cur_pair)
    cur1, cur2 = match.group(1).upper(), match.group(2).upper()    

    # Проверяем параметры                
    if not days.isnumeric() or (days.isnumeric() and 
            float(days) <= 0):    
        update.message.reply_text('Invalid amount of days.')
        return    
    days = float(days)

    if not rates.valid_currency(cur1):
        update.message.reply_text(f'Invalid currency: {cur1}')
        return 
    if not rates.valid_currency(cur2):
        update.message.reply_text(f'Invalid currency: {cur2}')
        return 

    # Получаем данные котировок за последние 'days' дней
    end_date = get_last_work_day()
    start_date = end_date - timedelta(days=(days - 1))   
    request_url = 'https://api.exchangeratesapi.io/history/'
    request_params = {'start_at': str(start_date), 'end_at': str(end_date),
        'base': cur2, 'symbols': cur1}    
    resp = requests.get(request_url, params=request_params)
    resp_rates = resp.json()['rates']   

    # Проверяем данные котировок
    if len(resp_rates) == 0: 
        update.message.reply_text('No exchange rate data is available for the selected currency.')     
        return   

    # Переводим котировки в списки значений x и y для графика
    x, y = [], []    
    for rate_date, rate_dict in sorted(resp_rates.items()): 
        x.append(rate_date)
        y.append(float(rate_dict[cur1]))
    
    # Формируем и возвращаем график    
    plt.plot(x, y)   
    plt.title(f'{cur1}/{cur2}') 
    plt.grid(True)
    plt.xticks(rotation=90)
    plt.savefig('chart.png', bbox_inches='tight')
    plt.clf()    
    context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=open('chart.png', 'rb'))    

def error(update, context):
    """Логирование ошибок в боте"""
    logger.warning(f'Update {update} caused error {context.error}')

def main():     
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', None)
    PORT = os.environ.get('PORT', None)
    if TOKEN is None or PORT is None:
        logger.error('Environment variable TELEGRAM_BOT_TOKEN or PORT is absent, can not start bot')
        sys.exit()    
    
    updater = Updater(TOKEN, use_context=True)     
    dp = updater.dispatcher

    dp.add_error_handler(error)
    dp.add_handler(CommandHandler("list", list_rates))
    dp.add_handler(CommandHandler("exchange", exchange))
    dp.add_handler(CommandHandler("history", history))

    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook('https://exchange-quotes-telegram-bot.herokuapp.com/' + TOKEN)
    updater.idle()

if __name__ == '__main__':
    main()