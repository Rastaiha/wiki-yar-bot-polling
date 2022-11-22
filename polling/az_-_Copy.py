from __future__ import print_function
import googleapiclient
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import dokuwiki

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, InlineQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import db_session, init_db
from models import *

import requests
from bs4 import BeautifulSoup
import sys
import json
import pickle
import os.path
import xmlrpc.client
import datetime
import csv
import subprocess
import re
import sqlalchemy
import random
from urllib.parse import unquote

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
# DOCUMENT_ID = '195j9eDD3ccgjQRttHhJPymLJUCOUjs-jmwTrekvdjFE'
# DOCUMENT_ID = '1qbioEIkxKVv1tRQouWtUXNAA-4pUhEMbBCnc9BtOV54'

admin_username = "AryanTR"
main_gp_id = -1001356415408

wiki_username = 'telegrambot'
wiki_password = 'xxxxxx'
wiki_url = 'https://wiki.rastaiha.ir'

wiki = dokuwiki.DokuWiki(wiki_url, wiki_username, wiki_password)



name_ids = {}

emojies = {}
f = open('emojies.txt', 'r', encoding='UTF-8')
emojies = json.loads(f.read())
f.close()

edit_size = 200
score_coef = {
    'edit': 4,
    'import': 5,
    'seen': 2
}



def get_file_json(doc_id):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('docs', 'v1', credentials=creds)

    # Retrieve the documents contents from the Docs service.
    document = service.documents().get(documentId=doc_id).execute()
    return document

def get_title_str(document):
    return '======' + document.get('title') +'======\n'

def text_formatter(text):
    return text.translate(non_bmp_map).replace('\t',' ')

def get_paragraph_element_str(element):
    if 'textRun' in element:
        x = text_formatter(element['textRun']['content'])
        if len(x.strip()) == 0:
            return ''
        if  element['textRun']['textStyle'].get('bold'):
            x = '**' + x + '**'
        if 'link' in element['textRun']['textStyle']:
            x = '[[' + element['textRun']['textStyle']['link']['url'] + '|' + x + ']]'
        return x
    else:
        return ''

def get_bullet_prefix(document, list_id, nesting_level):
    bullet = document['lists'][list_id]['listProperties']['nestingLevels'][nesting_level]
    bullet_symbol = '-'
    if 'glyphSymbol' in bullet:
        bullet_symbol = '*'
    return ((nesting_level + 1)*2) * ' ' + bullet_symbol + ' '

def get_structural_element_str(document, element):
    print(element)
    try:
        ss = ''
        for e in element['paragraph']['elements']:
            ss += get_paragraph_element_str(e)
        if len(ss.strip()) ==0:
            return ''
        if element['paragraph']['paragraphStyle'].get('namedStyleType') == 'HEADING_1':
            ss = '=====' + ss.strip() + '====='
        if element['paragraph']['paragraphStyle'].get('namedStyleType') == 'HEADING_2':
            ss = '====' + ss.strip() + '===='
        if element['paragraph']['paragraphStyle'].get('namedStyleType') == 'HEADING_3':
            ss = '===' + ss.strip() + '==='
        if element['paragraph']['paragraphStyle'].get('namedStyleType') == 'HEADING_4':
            ss = '==' + ss.strip() + '=='
        if element['paragraph']['paragraphStyle'].get('namedStyleType') == 'NORMAL_TEXT' and element['paragraph']['paragraphStyle'].get('alignment') == 'JUSTIFIED' and 'bullet' not in element['paragraph']:
            ss = '###\n' + ss + '\n###\n'
        if 'bullet' in element['paragraph']:
            ss = '\n' + get_bullet_prefix(document, element['paragraph']['bullet']['listId'], element['paragraph']['bullet'].get('nestingLevel', 0)) + ss.strip()
        else:
            ss = '\n\n' + ss
        return ss
    except:
        return ''

def get_document_str(doc_id):
    document = get_file_json(doc_id)

    f = open('tempjson.txt','w', encoding='UTF-8')
    #f.write(str(document))
    f.close()
    print('The title of the document is: {}'.format(document.get('title')))
    print(len(document['body']['content']))
    s = get_title_str(document)
    for c in document['body']['content']:
        s += get_structural_element_str(document, c)
    return s

#print(get_document_str('1qbioEIkxKVv1tRQouWtUXNAA-4pUhEMbBCnc9BtOV54'))
f = open('temp.txt','w')
f.write(get_document_str('1KLhwY4lcXzfECjVEpFycDktaoNk0J7AyfZsGvf0hpxs'))
f.close()



def name_to_id(name):
    if name in name_ids:
        return name_ids[name]
    name_ids[name] = len(name_ids.keys())
    return name_ids[name]

def id_to_name(idd):
    idd = int(idd)
    for name in name_ids:
        if name_ids[name] == idd:
            return name




def normalize(text):
    res = text
    f = open('converter.txt', 'r', encoding='UTF-8')
    lines = [line.rstrip('\n') for line in f]
    for line in lines:
        l = line.split(',')
        res = res.replace(l[0], l[1] + ' ')
    return res

def anormalize(text):
    res = text
    f = open('converter.txt', 'r', encoding='UTF-8')
    lines = [line.rstrip('\n') for line in f]
    for line in lines:
        l = line.split(',')
        res = res.replace(l[1], l[0] + ' ')
    return res
    



def to_farsi(text):
    try:
        r = requests.post(
            'http://syavash.com/portal/modules/pinglish2farsi/convertor.php?lang=fa',
            data = {
                'pinglish': text,
                'action': 'convert'
                }
            )
        soup = BeautifulSoup(r.text, 'html.parser')
        p_text = soup.findAll('a')[0].string
        return p_text
    except:
        return text

def get_all_namespaces():
    d = {'':0}
    all_pages = wiki.pages.list()
    for page in all_pages:
        l = page['id'].split(':')
        s = ''
        for i in range(len(l)-1):
            if len(s) > 0:
                s += ':'
            s += l[i]
            d[s] = i + 1
    return d

def get_child_namespaces(namespaces_dic, namespace=''):
    l = []
    lvl = namespaces_dic[namespace]
    for n in namespaces_dic:
        if namespace in n:
            if namespaces_dic[n] == namespaces_dic[namespace] + 1:
                l.append(n)
    return l

def get_parent_namespace(namespace):
    l = namespace.split(':')
    s = ''
    for i in range(len(l)-1):
        if len(s) > 0:
            s += ':'
        s += l[i]
    return s




def compute_score(user):
    return score_coef['import'] * user.num_import + score_coef['edit'] * user.num_edit + score_coef['seen'] * user.num_seen

def get_best(item):
    al = []
    for user in db_session.query(User).all():
        al.append({
            'user': user,
            'edit': user.num_edit,
            'import': user.num_import,
            'seen': user.num_seen,
            'score': compute_score(user)
            })
    maxi = -1
    maxx = None
    for u in al:
        if u[item] > maxi:
            maxi = u[item]
            maxx = u['user']
    return maxx, maxi






    
def hello(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        name = user.persian_name
        update.message.reply_text(
            'سلام {}!'.format(name))
        if 6 <= datetime.datetime.now().hour < 12:
            update.message.reply_text(
                'صبح شما بخير!')
    except AttributeError as ae:
        print(ae)
    except:
        print(sys.exc_info()[0])

def download(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        user.state = States.get_link
        db_session.commit()
        update.message.reply_text('بسيار هم خوب. لطفا لينک مورد نظر رو بفرستين.')
    except:
        print(sys.exc_info()[0])

def import_google_doc(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        user.state = States.get_doc_id
        db_session.commit()
        update.message.reply_text('بسيار هم خوب. لطفا آیدی یا لینک مورد نظر را وارد کنید.')
    except:
        print(sys.exc_info()[0])

def reset(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        user.state = States.default
        db_session.commit()
        update.message.reply_text('انجام شد.')
    except:
        print(sys.exc_info()[0])

def profile(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        update.message.reply_text('شما دارای %d ادیت(%s)، %d وارد کردن(%s) و %d دانلود سند(%s) هستید.\nامتیاز شما در مجموع %d(%s) است.'%
            (user.num_edit, emojies['edit'], user.num_import, emojies['import'], user.num_seen, emojies['seen'],
             compute_score(user), emojies['star']))
    except:
        print(sys.exc_info()[0])

def leaderboard(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        s = ''
        user, num = get_best('seen')
        s += 'بیش‌ترین تعداد دانلود(%s) در اختیار <b>%s</b> است با دیدن %d صفحه\n\n' % (emojies['seen'], user.real_name, num)

        user, num = get_best('edit')
        s += 'بیش‌ترین تعداد ویرایش(%s) در اختیار <b>%s</b> است با ویرایش %d صفحه\n\n' % (emojies['edit'], user.real_name, num)

        user, num = get_best('import')
        s += 'بیش‌ترین تعداد وارد کردن(%s) در اختیار <b>%s</b> است با وارد کردن %d صفحه\n\n' % (emojies['import'], user.real_name, num)

        user, num = get_best('score')
        s += 'بیش‌ترین امتیاز کل(%s) در اختیار <b>%s</b> است با %d امتیاز\n\n' % (emojies['star'], user.real_name, num)

        update.message.reply_text(s, parse_mode=telegram.ParseMode.HTML)
    except KeyError as e:
        print(e)
    except:
        print(sys.exc_info()[0])



def help_me(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        f = open('helps/help_0.txt', 'r', encoding='UTF-8')
        text = f.read()
        f.close()
        f = open('helps/next_0.txt', 'r', encoding='UTF-8')
        s = f.read()
        n = json.loads(s)
        f.close()
        x = []
        bef = []
        for i in range(len(n)):
            if i % 2 == 0:
                x.append(bef)
                bef = []
            bef.append(InlineKeyboardButton(n[i][0], callback_data='help_'+str(n[i][1])))
        x.append(bef)
        update.message.reply_text(text, parse_mode=telegram.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(x))
    except telegram.error.BadRequest as bd:
        print(bd)
    except json.decoder.JSONDecodeError as e:
        print(e)
    except:
        print(sys.exc_info()[0])

def get_edit(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        all_pages = wiki.pages.list()
        page = random.choice(all_pages)['id']
        content = wiki.pages.get(page)
        start = random.randint(0, len(content) - 1)
        while content[start] != '\n' and start > 0:
            start -= 1
        end = start + edit_size
        if end > len(content):
            end = len(content)
        while content[end - 1] != '\n' and end < len(content):
            end += 1
        chunk = content[start:end].strip()

        tlg_id = update.message.from_user.id
        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        user.state = States.edit
        user.cache = page
        user.cache1 = chunk
        db_session.commit()

        update.message.reply_text('متن زیر از صفحه‌ی <i>{}</i> انتخاب شده. لطفا به اینترها و دیگر علائم مخصوص دوکوویکی دست نزنید.'.format(page) + 
            'اگر از ادیت منصرف شدید دستور /cancel را بزنید و درصورتی که می‌خواهید صفحه‌ی دیگری را ادیت کنید /next را بزنید.' + 
            ' اگر قصد دارید این تکه از فایل را ذخیره کنید و بعدا آن را ویرایش کنید دستور /save را بزنید.',
            parse_mode=telegram.ParseMode.HTML)
        update.message.reply_text('`' + anormalize(chunk) + '`', parse_mode=telegram.ParseMode.MARKDOWN_V2)
    except telegram.error.BadRequest as e:
        print(e)
    except IndexError as ie:
        print(ie)
    except:
        print(sys.exc_info()[0])

def save(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return 

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]

        if user.state != States.edit:
            return

        file = File(
            page=user.cache,
            user=user,
            text=user.cache1
            )
        db_session.add(file)
        user.cache = ''
        user.cache1 = ''
        user.state = States.default
        db_session.commit()
        update.message.reply_text('ذخیره شد. حالا چه خدمتی از دست‌ام ساخته‌ست؟')
    except:
        print(sys.exc_info()[0])

def get_state(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return 

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        update.message.reply_text(str(user.state))
    except:
        print(sys.exc_info()[0])

def explore(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        s = 'فضاها و فايل‌هاي زير موجود هستند:\n'
        x = []
        namespaces = get_child_namespaces(get_all_namespaces())
        for namespace in namespaces:
            x.append([InlineKeyboardButton(emojies['folder'] + namespace, callback_data='explore_'+ str(name_to_id(namespace)))])
        update.message.reply_text(s, reply_markup=InlineKeyboardMarkup(x))
    except:
        print(sys.exc_info()[0])

def my_saves(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return

        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        s = 'شما تکه فایل‌های زیر را جهت ویرایش ذخیره کرده‌اید:\n'
        x = []
        for file in user.files:
            x.append([InlineKeyboardButton(emojies['file'] + file.page, callback_data='saved_'+ str(file.id))])
        if len(x) > 0:
            update.message.reply_text(s, reply_markup=InlineKeyboardMarkup(x))
        else:
            update.message.reply_text('شما در حال حاضر هیچ تکه فایلی برای ویرایش ذخیره نکرده‌اید.' + emojies['sad'])
    except:
        print(sys.exc_info()[0])

def start(update, context):
    try:
        tlg_user = update.message.from_user

        verified = False
        try:
            if updater.bot.get_chat(main_gp_id).get_member(tlg_user.id).status in ['creator', 'administrator', 'member', 'restricted']:
                verified = True
            print(updater.bot.get_chat(main_gp_id).get_member(tlg_user.id))
        except:
            print(sys.exc_info()[0])
        if not verified:
            update.message.reply_text('متاسفانه هویت رستایی شما تایید نشد. اگر عضو گروه خانواده هستید و این پیام را دریافت کرده‌اید به ادمین پیام دهید.')
            return

        if db_session.query(User).filter(User.tlg_id ==tlg_user.id).count():
            update.message.reply_text('استاد اين‌قدر استارت نزن ناموسا:)))')
            return
        user = User(
            username=tlg_user.username,
            first_name= tlg_user.first_name,
            last_name=tlg_user.last_name,
            tlg_id=tlg_user.id,
            state=States.get_real_name,
            persian_name=to_farsi(tlg_user.first_name),
            real_name = tlg_user.first_name + ' ' + tlg_user.last_name,
            cache='',
            cache1='',
            num_seen = 0,
            num_import = 0,
            num_edit = 0
        )
        db_session.add(user)
        db_session.commit()
        update.message.reply_text(
            'سلام {}!'.format(user.persian_name))
        update.message.reply_text('به‌به خوش اومدين!')
        update.message.reply_text('در ابتدا لطفا نام کامل خود را وارد بفرمایید.')
    except sqlalchemy.exc.InvalidRequestError as err:
        print(err)
    except:
        print(sys.exc_info()[0])

def sxp(update, context):
    update.message.reply_text('حقيقتا سطح!')

def download_contents(update, context):
    try:
        tlg_id = update.message.from_user.id
        try:
            user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        except:
            update.message.reply_text('لطفا اول فرمان /start را بزنید.')
            return
        url = wiki_url
        s = requests.Session()
        r = s.post(url, data = {
            'sectok': '',
            'id': 'برگ آغازین',
            'do': 'login',
            'u': wiki_username,
            'p': wiki_password
        })
        pdf_name = 'فهرست' + '.pdf'
        url = 'https://wiki.rastaiha.ir/%D9%88%DB%8C%DA%A9%DB%8C/%D9%81%D9%87%D8%B1%D8%B3%D8%AA_%D8%B5%D9%81%D8%AD%D9%87_%D9%87%D8%A7?do=export_pdf'
        r = s.get(url, allow_redirects=True)
        open(pdf_name, 'wb').write(r.content)
        context.bot.send_document(update.message.chat_id,
                        document=open(pdf_name, 'rb')
        )
        os.system('del ' + pdf_name)
        user.num_seen += 1
        db_session.commit()

    except:
        print(sys.exc_info()[0])

def migrate(update, context):
    try:
        if update.message.from_user.username != admin_username:
            return
        init_db()
        update.message.reply_text('چشم استاد.')
    except NameError as ne:
        print(ne)
    except:
        print(sys.exc_info()[0])

def send_messages(update, context):
    try:
        if update.message.from_user.username != admin_username:
            return
        f = open('msgs.txt', 'r', encoding='UTF-8')
        for line in f.read().strip().split('\n'):
            l = line.split(',')
            if l[0] == 'all':
                for user in db_session.query(User).all():
                    context.bot.send_message(user.tlg_id, l[1].replace('<<name>>', user.persian_name))
            else:
                #print(db_session.query(User).filter(User.username==l[0][1:]).all())
                user = db_session.query(User).filter(User.username==l[0][1:]).all()[0]
                context.bot.send_message(user.tlg_id, l[1].replace('<<name>>', user.persian_name))
    except NameError as ne:
        print(ne)
    except telegram.error.BadRequest as e:
        print(e)
    except IndexError as e:
        print(e)
    except telegram.error.Unauthorized as e:
        print(e)
    except:
        print(sys.exc_info()[0])

def stat(update, context):
    try:
        if update.message.from_user.username != admin_username:
            return
        for user in db_session.query(User).all():
            update.message.reply_text(user.persian_name + ' به آيدي @' + user.username + ' با ' + 
                str(user.num_seen) + ':' + str(user.num_import) + ':' + str(user.num_edit))
    except NameError as ne:
        print(ne)
    except TypeError as te:
        print(te)
    except:
        print(sys.exc_info()[0])




def change_name(update, context, user, text):
    name = re.search(r'«(\w+)»', text).group(1)
    if user.persian_name==name:
        update.message.reply_text('خب من هم که همينو گفته بودم!')
        return False
    user.persian_name = name
    db_session.commit()
    update.message.reply_text('شرمنده {}، نتونسته بودم اسم‌تو درست بخونم.'.format(user.persian_name))
    return True

def congrat_eid(update, context, user, text):
    update.message.reply_text('سلام {}. مرسي!'.format(user.persian_name))
    return True

def download_link(update, context, user, text):
    url = wiki_url
    s = requests.Session()
    r = s.post(url, data = {
        'sectok': '',
        'id': 'برگ آغازین',
        'do': 'login',
        'u': wiki_username,
        'p': wiki_password
    })
    pdf_name = unquote(text.split('/')[-1]) + '.pdf'
    url = text +  '?do=export_pdf'
    r = s.get(url, allow_redirects=True)
    open(pdf_name, 'wb').write(r.content)
    context.bot.send_document(update.message.chat_id,
                    document=open(pdf_name, 'rb')
    )
    os.system('del ' + pdf_name)
    user.num_seen += 1
    db_session.commit()
    return True

def get_doc_id(update, context, user, text):
    try:
        user.cache = text
        print(len(get_file_json(text)))
        db_session.commit()
        update.message.reply_text('ممنون حال آدرس مورد نظر را وارد کنید.')
        return True
    except googleapiclient.errors.HttpError:
        try:
            id = re.search(r'docs.google.com/document/d/(\S+)/edit', text).group(1)
            user.cache = id
            print(len(get_file_json(id)))
            db_session.commit()
            update.message.reply_text('ممنون حال آدرس مورد نظر را وارد کنید.')
            return True
        except:
            update.message.reply_text('شرمنده‌ام ولی فکر کنم آیدی درستی وارد نکرده‌اید. اگر از آیدی مطمئن لطفا هستید دسترسی‌های داک را بررسی فرمایید'
             + ' و دوباره آیدی درست را وارد کنید.' 
             + emojies["sad"])
            return False

def get_doc_address(update, context, user, text):
    wiki.pages.set(text, get_document_str(user.cache), sum='به دستور ' + user.real_name)
    user.cache = ''
    user.num_import += 1
    db_session.commit()
    update.message.reply_text(
        '<a href="{}">انجام شد.</a>'.format(wiki_url + '/' + text.replace(':', '/')),
        parse_mode=telegram.ParseMode.HTML
        )
    return True

def set_edit(update, context, user, text):
    content = wiki.pages.get(user.cache)
    new_content = content.replace(user.cache1, normalize(text))
    wiki.pages.set(user.cache, new_content, sum='به دستور ' + user.real_name)
    user.cache = ''
    user.cache1 = ''
    user.num_edit += 1
    db_session.commit()
    update.message.reply_text(
        'ممنون.' + random.choice(emojies['thanks']),
        parse_mode=telegram.ParseMode.HTML
        )
    return True

def realname(update, context, user, text):
    user.real_name = text
    db_session.commit()
    update.message.reply_text('حل‌ه.')
    update.message.reply_text('آیا مایلید از نحوه‌ی کار با بات اطلاع یابید؟ دستور /help را وارد کنید.')
    return True

def time(update, context):
    try:
        #print('hey')
        tlg_id = update.message.from_user.id
        user = db_session.query(User).filter(User.tlg_id==tlg_id).all()[0]
        #print(user)
        text = update.message.text
        #print(text)
        rules = [
            # (intiail_state, 'text_regex', func, 'next_state_true', 'next_state_false)
            (States.get_link, '\w+', download_link, States.default, States.default),
            (States.get_doc_id, '\w+', get_doc_id, States.get_address, States.get_doc_id),
            (States.get_address, '\w+', get_doc_address, States.default, States.default),
            (States.edit, '\w+', set_edit, States.default, States.default),
            (States.get_real_name, '\w+', realname, States.default, States.default),
            ('', 'اسم من «\w+»ه.', change_name, 'x', 'x'),
            ('', '\w*عید\w*', congrat_eid, 'x', 'x')

        ]
        for rule in rules:
            if re.search(rule[0], user.state) is None:
                continue
            if re.search(rule[1], text) is None:
                continue
            if rule[2](update, context, user, text):
                if rule[3] != 'x':
                    user.state = rule[3]
            else:
                if rule[4] != 'x':
                    user.state = rule[4]
            db_session.commit()
            return
        print(user.username)
        try:
            print(text)
        except:
            pass
        #for c in text:
        #    print(ord(c))
        #    print(c)
        #f = open('emojies.txt', 'r' ,encoding='UTF-8')
        #e = f.readline().rstrip('\n')
        #f.close()
        #print(e in text)
        update.message.reply_text("شرمنده نمی‌فهمم چی می‌گین." + emojies['sad'])
    except NameError as ne:
        print(ne)
    except TypeError as te:
        print(te)
    except AttributeError as ae:
        print(ae)
    except IndexError as ie:
        print(ie)
    except UnicodeEncodeError as e:
        print(e)
    except:
        print(sys.exc_info()[0])



def button(update, context):
    try:
        try:
            print(update.callback_query)
        except:
            pass
        print(update.callback_query.__dict__.keys())
        user = db_session.query(User).filter(User.tlg_id==update.callback_query['from_user']['id']).all()[0]
        if 'select_' in update.callback_query['data']:
            file_name = id_to_name(int(update.callback_query['data'][7:]))
            x = []
            x.append([InlineKeyboardButton(emojies['download'] + 'دانلود', callback_data='download_'+str(name_to_id(file_name)))])
            x.append([InlineKeyboardButton(emojies['link'] + 'لینک', callback_data='link_'+str(name_to_id(file_name)))])
            x.append([InlineKeyboardButton(emojies['back'] + 'بازگشت', callback_data='explore_'+str(name_to_id(get_parent_namespace(file_name))))])
            update.callback_query.edit_message_text('شما در فايل <i>{}</i> هستيد.\nچه کنم؟:'.format(file_name),
                           parse_mode=telegram.ParseMode.HTML
                           )
            update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(x))
        if 'link_' in update.callback_query['data']:
            file_name = id_to_name(int(update.callback_query['data'][5:]))
            update.callback_query.edit_message_text('<a href="%s">%s</a>'%(wiki_url + '/' + file_name.replace(':','/'), file_name.split(':')[-1]),
                           parse_mode=telegram.ParseMode.HTML
                           )
        if 'download_' in update.callback_query['data']:
            file_name = id_to_name(int(update.callback_query['data'][9:]))
            url = wiki_url
            s = requests.Session()
            r = s.post(url, data = {
                'sectok': '',
                'id': 'برگ آغازین',
                'do': 'login',
                'u': wiki_username,
                'p': wiki_password
            })
            pdf_name = file_name.split(':')[-1] + '.pdf'
            url = url + '/' + file_name.replace(':', '/') +  '?do=export_pdf'
            r = s.get(url, allow_redirects=True)
            open(pdf_name, 'wb').write(r.content)
            context.bot.send_document(
                            update.callback_query['message']['chat_id'],
                            document=open(pdf_name, 'rb')
                           )
            os.system('del ' + pdf_name)
            user.num_seen += 1
            db_session.commit()
        if 'explore_' in update.callback_query['data']:
            namespace = id_to_name(int(update.callback_query['data'][8:]))
            namespaces = get_child_namespaces(get_all_namespaces(), namespace)
            x = []
            for n in namespaces:
                x.append([InlineKeyboardButton(emojies['folder'] + n.split(':')[-1], callback_data='explore_'+str(name_to_id(n)))])
            files = wiki.pages.list(namespace)
            for file in files:
                if get_parent_namespace(file['id']) != namespace:
                    continue
                x.append([InlineKeyboardButton(emojies['file'] + file['id'].split(':')[-1], callback_data='select_'+str(name_to_id(file['id'])))])
            
            x.append([InlineKeyboardButton(emojies['back'] + 'بازگشت', callback_data='explore_'+str(name_to_id(get_parent_namespace(namespace))))])
            update.callback_query.edit_message_text('شما در فضاي <i>{}</i> هستيد.\nفضاها و فايل‌هاي زير موجود هستند:'.format(namespace),
                           parse_mode=telegram.ParseMode.HTML
                           )
            update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(x))
        if 'saved_' in update.callback_query['data']:
            id = int(update.callback_query['data'][6:])
            file = db_session.query(File).filter(File.id==id).all()[0]
            context.bot.delete_message(
                           chat_id=update.callback_query['message']['chat_id'],
                           message_id=update.callback_query['message']['message_id']
                           )
            context.bot.send_message(update.callback_query['message']['chat_id'],
                            'متن زیر از صفحه‌ی <i>{}</i> انتخاب شده. لطفا به اینترها و دیگر علائم مخصوص دوکوویکی دست نزنید.'.format(file.page) + 
                            'اگر از ادیت منصرف شدید دستور /cancel را بزنید و درصورتی که می‌خواهید صفحه‌ی دیگری را ادیت کنید /next را بزنید.' + 
                            ' اگر قصد دارید این تکه از فایل را ذخیره کنید و بعدا آن را ویرایش کنید حتما دوباره دستور /save را بزنید.',
                            parse_mode=telegram.ParseMode.HTML)
            context.bot.send_message(
                            update.callback_query['message']['chat_id'],
                            '`' + anormalize(file.text) + '`',
                            parse_mode=telegram.ParseMode.MARKDOWN_V2
                           )
            user.state = States.edit
            user.cache = file.page
            user.cache1 = file.text
            db_session.query(File).filter(File.id==id).delete()
            db_session.commit()
        if 'help_' in update.callback_query['data']:
            id = int(update.callback_query['data'][5:])
            f = open('helps/help_' + str(id) + '.txt', 'r', encoding='UTF-8')
            text = f.read()
            f.close()
            f = open('helps/next_' + str(id) + '.txt', 'r', encoding='UTF-8')
            s = f.read()
            n = json.loads(s)
            f.close()
            x = []
            bef = []
            for i in range(len(n)):
                if i % 2 == 0:
                    x.append(bef)
                    bef = []
                bef.append(InlineKeyboardButton(n[i][0], callback_data='help_'+str(n[i][1])))
            x.append(bef)
            update.callback_query.edit_message_text(text,
                            parse_mode=telegram.ParseMode.HTML
                           )
            update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(x))


        return
    except AttributeError as ae:
        print(ae)
    except KeyError as ke:
        print(ke)
    except NameError as ne:
        print(ne)
    except TypeError as te:
        print(te)
    except ValueError as ve:
        print(ve)
    except telegram.error.BadRequest as bd:
        print(bd)
    except subprocess.CalledProcessError as e:
        print(e)
    except:
        print(sys.exc_info()[0])
    update.callback_query.edit_message_text('مشکلي پيش آمده لطفا دستور را از ابتدا وارد کنيد.')

TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
REQUEST_KWARGS={
#    'proxy_url': 'socks5h://127.0.0.1:9150'
}
updater = Updater(TOKEN, use_context=True, request_kwargs=REQUEST_KWARGS)
print(updater.bot.get_me())


updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('sxp', sxp))
updater.dispatcher.add_handler(CommandHandler('migrate', migrate))
updater.dispatcher.add_handler(CommandHandler('send_messages', send_messages))
updater.dispatcher.add_handler(CommandHandler('stat', stat))
updater.dispatcher.add_handler(CommandHandler('explore', explore))
updater.dispatcher.add_handler(CommandHandler('download', download))
updater.dispatcher.add_handler(CommandHandler('import_google_doc', import_google_doc))
updater.dispatcher.add_handler(CommandHandler('edit', get_edit))
updater.dispatcher.add_handler(CommandHandler('cancel', reset))
updater.dispatcher.add_handler(CommandHandler('next', get_edit))
updater.dispatcher.add_handler(CommandHandler('get_state', get_state))
updater.dispatcher.add_handler(CommandHandler('profile', profile))
updater.dispatcher.add_handler(CommandHandler('save', save))
updater.dispatcher.add_handler(CommandHandler('my_saves', my_saves))
updater.dispatcher.add_handler(CommandHandler('leaderboard', leaderboard))
updater.dispatcher.add_handler(CommandHandler('help', help_me))
updater.dispatcher.add_handler(CommandHandler('contents', download_contents))
updater.dispatcher.add_handler(CallbackQueryHandler(button))
updater.dispatcher.add_handler(MessageHandler(Filters.text , time,pass_job_queue=True))


updater.start_polling()
updater.idle()



