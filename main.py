#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Save Insta - تطبيق تحميل إنستغرام
Copyright © 2026 Youssef Mansouri
"""

import os
import sys
import json
import re
import time
import sqlite3
import threading

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

try:
    import yt_dlp
except ImportError:
    os.system(f"{sys.executable} -m pip install yt-dlp -q")
    import yt_dlp

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import ListProperty, NumericProperty
from kivy.animation import Animation
from kivy.metrics import dp

# iOS Colors
IOS_BLUE = (0.0, 0.48, 1.0, 1)
IOS_GRAY = (0.56, 0.56, 0.58, 1)
IOS_LIGHT_GRAY = (0.95, 0.95, 0.97, 1)
IOS_WHITE = (1, 1, 1, 1)
IOS_BLACK = (0, 0, 0, 1)
IOS_GREEN = (0.2, 0.78, 0.35, 1)
IOS_RED = (1.0, 0.23, 0.19, 1)

Window.clearcolor = IOS_LIGHT_GRAY

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saveinsta.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, created_at REAL)')
    conn.commit()
    conn.close()

def cache_get(key):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value, created_at FROM cache WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        if row and time.time() - row[1] < 600:
            return json.loads(row[0])
    except:
        pass
    return None

def cache_set(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, json.dumps(value), time.time()))
        conn.commit()
        conn.close()
    except:
        pass

init_db()

UAS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
]
def get_ua():
    return __import__('random').choice(UAS)

# --------------------------------------------------------------------------- #
# Scraping
# --------------------------------------------------------------------------- #
def scrape_profile(username):
    username = username.strip().lstrip("@")
    cached = cache_get(f"prof:{username}")
    if cached:
        return cached

    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": get_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.instagram.com/",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 404:
            return {"error": "الحساب غير موجود"}
        if r.status_code == 429:
            return {"error": "تم الحظر مؤقتاً، جرب بعد 10 دقائق"}

        text = r.text
        m = re.search(r'window\._sharedData\s*=\s*({.+?});</script>', text)
        if m:
            data = json.loads(m.group(1))
            user = data['entry_data']['ProfilePage'][0]['graphql']['user']
            result = {
                "username": user.get('username', username),
                "full_name": user.get('full_name', ''),
                "biography": user.get('biography', ''),
                "followers": user.get('edge_followed_by', {}).get('count', 0),
                "following": user.get('edge_follow', {}).get('count', 0),
                "posts": user.get('edge_owner_to_timeline_media', {}).get('count', 0),
                "is_private": user.get('is_private', False),
                "is_verified": user.get('is_verified', False),
                "pic_url": user.get('profile_pic_url_hd', user.get('profile_pic_url', '')),
            }
            cache_set(f"prof:{username}", result)
            return result

        bio = ""
        bio_m = re.search(r'"biography":("(?:\\.|[^"\\])*"|null)', text)
        if bio_m and bio_m.group(1) != "null":
            try:
                bio = json.loads(bio_m.group(1))
            except:
                bio = bio_m.group(1).strip('"')

        name = ""
        name_m = re.search(r'"full_name":("(?:\\.|[^"\\])*"|null)', text)
        if name_m and name_m.group(1) != "null":
            try:
                name = json.loads(name_m.group(1))
            except:
                name = name_m.group(1).strip('"')

        followers = 0
        f_m = re.search(r'"edge_followed_by":\{"count":(\d+)\}', text)
        if f_m:
            followers = int(f_m.group(1))

        following = 0
        fg_m = re.search(r'"edge_follow":\{"count":(\d+)\}', text)
        if fg_m:
            following = int(fg_m.group(1))

        posts = 0
        p_m = re.search(r'"edge_owner_to_timeline_media":\{"count":(\d+)\}', text)
        if p_m:
            posts = int(p_m.group(1))

        is_private = '"is_private":true' in text
        is_verified = '"is_verified":true' in text

        pic_url = ""
        pic_m = re.search(r'"profile_pic_url_hd":"(https://[^"]+)"', text)
        if not pic_m:
            pic_m = re.search(r'"profile_pic_url":"(https://[^"]+)"', text)
        if pic_m:
            pic_url = pic_m.group(1)

        result = {
            "username": username,
            "full_name": name,
            "biography": bio,
            "followers": followers,
            "following": following,
            "posts": posts,
            "is_private": is_private,
            "is_verified": is_verified,
            "pic_url": pic_url,
        }
        cache_set(f"prof:{username}", result)
        return result

    except Exception as e:
        return {"error": f"خطأ: {str(e)[:200]}"}

def download_media(url, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    opts = {
        'outtmpl': os.path.join(download_dir, '%(title).80s.%(ext)s'),
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'user_agent': get_ua(),
        'retries': 2,
        'socket_timeout': 20,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None, "فشل التحميل"
        files = [
            os.path.join(download_dir, f)
            for f in sorted(os.listdir(download_dir))
            if os.path.isfile(os.path.join(download_dir, f)) and not f.endswith(('.json', '.txt', '.part'))
        ]
        if not files:
            return None, "لم يتم العثور على ملفات"
        return files, None
    except Exception as e:
        return None, str(e)[:300]

# --------------------------------------------------------------------------- #
# iOS Style Widgets
# --------------------------------------------------------------------------- #
class iOSButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = IOS_BLUE
        self.color = IOS_WHITE
        self.font_size = '16sp'
        self.bold = True
        self.size_hint_y = None
        self.height = dp(50)
        self.border_radius = [dp(12), dp(12), dp(12), dp(12)]
        with self.canvas.before:
            Color(*IOS_BLUE)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)]*4)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class iOSCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = dp(16)
        self.spacing = dp(12)
        self.size_hint_y = None
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)]*4)
            Color(0.9, 0.9, 0.92, 0.5)
            self.shadow = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(16)), width=0.5)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class iOSInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.size_hint_y = None
        self.height = dp(50)
        self.font_size = '16sp'
        self.padding = [dp(16), dp(14), dp(16), dp(14)]
        self.background_normal = ''
        self.background_active = ''
        self.background_color = IOS_WHITE
        self.foreground_color = IOS_BLACK
        self.hint_text_color = IOS_GRAY
        self.cursor_color = IOS_BLUE

class iOSLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = IOS_BLACK
        self.font_size = '15sp'
        self.text_size = (None, None)

class StatBox(BoxLayout):
    def __init__(self, label, value, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.add_widget(Label(text=f"{value:,}", font_size='18sp', bold=True, color=IOS_BLACK))
        self.add_widget(Label(text=label, font_size='12sp', color=IOS_GRAY))

class ProfileCard(iOSCard):
    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.bind(minimum_height=self.setter('height'))

        # Profile Image
        if data.get('pic_url'):
            img_container = BoxLayout(size_hint_y=None, height=dp(120), padding=dp(20))
            img = AsyncImage(
                source=data['pic_url'],
                size_hint=(None, None),
                size=(dp(100), dp(100)),
                allow_stretch=True,
                keep_ratio=True
            )
            img_container.add_widget(Widget())
            img_container.add_widget(img)
            img_container.add_widget(Widget())
            self.add_widget(img_container)

        # Name
        name = data.get('full_name') or data.get('username')
        self.add_widget(Label(
            text=name,
            font_size='22sp',
            bold=True,
            color=IOS_BLACK,
            size_hint_y=None,
            height=dp(35)
        ))
        self.add_widget(Label(
            text=f"@{data.get('username')}",
            font_size='14sp',
            color=IOS_GRAY,
            size_hint_y=None,
            height=dp(25)
        ))

        # Stats Row
        stats = GridLayout(cols=3, size_hint_y=None, height=dp(70), padding=dp(10))
        stats.add_widget(StatBox('منشورات', data.get('posts', 0)))
        stats.add_widget(StatBox('متابعون', data.get('followers', 0)))
        stats.add_widget(StatBox('يتابع', data.get('following', 0)))
        self.add_widget(stats)

        # Badges
        badges = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        if data.get('is_private'):
            badges.add_widget(self._badge('🔒 خاص', (1, 0.23, 0.19, 0.1), IOS_RED))
        else:
            badges.add_widget(self._badge('🌐 عام', (0.2, 0.78, 0.35, 0.1), IOS_GREEN))
        if data.get('is_verified'):
            badges.add_widget(self._badge('✅ موثّق', (0.0, 0.48, 1.0, 0.1), IOS_BLUE))
        self.add_widget(badges)

        # Bio
        bio = data.get('biography', 'لا يوجد بايو')
        self.add_widget(Label(
            text=bio,
            font_size='14sp',
            color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None,
            height=dp(80),
            text_size=(Window.width - dp(80), None)
        ))

        # Action Buttons
        actions = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(12))
        
        copy_btn = iOSButton(text='📋 نسخ البايو', background_color=IOS_BLUE)
        copy_btn.bind(on_press=lambda x: self.copy_bio(bio))
        actions.add_widget(copy_btn)

        dl_btn = iOSButton(text='📥 تحميل الصورة', background_color=IOS_GREEN)
        dl_btn.bind(on_press=lambda x: self.dl_pic(data.get('pic_url'), data.get('username')))
        actions.add_widget(dl_btn)

        self.add_widget(actions)

    def _badge(self, text, bg_color, text_color):
        lbl = Label(
            text=text,
            font_size='12sp',
            color=text_color,
            size_hint_x=None,
            width=dp(80)
        )
        with lbl.canvas.before:
            Color(*bg_color)
            RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(12)]*4)
        return lbl

    def copy_bio(self, text):
        Clipboard.copy(text)
        self.show_toast('✅ تم نسخ البايو')

    def dl_pic(self, url, username):
        if not url:
            self.show_toast('❌ لا توجد صورة')
            return
        self.show_toast('⏳ جاري التحميل...')
        threading.Thread(target=self._dl_thread, args=(url, username)).start()

    def _dl_thread(self, url, username):
        try:
            try:
                from android.storage import primary_external_storage_path
                base = primary_external_storage_path()
            except:
                base = os.path.expanduser("~")
            sd = os.path.join(base, "Download", "SaveInsta")
            os.makedirs(sd, exist_ok=True)
            ext = ".png" if ".png" in url else ".jpg"
            path = os.path.join(sd, f"{username}_profile{ext}")
            r = requests.get(url, headers={"User-Agent": get_ua()}, timeout=20)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                Clock.schedule_once(lambda dt: self.show_toast('✅ تم حفظ الصورة'), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_toast('❌ فشل التحميل'), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_toast(f'❌ خطأ'), 0)

    def show_toast(self, msg):
        popup = Popup(
            title='',
            content=Label(text=msg, font_size='16sp', color=IOS_WHITE),
            size_hint=(0.7, 0.15),
            background_color=(0, 0, 0, 0.8),
            separator_height=0
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

# --------------------------------------------------------------------------- #
# Main App
# --------------------------------------------------------------------------- #
class SaveInstaApp(App):
    def build(self):
        self.title = 'Save Insta'
        
        root = BoxLayout(orientation='vertical')
        
        # Header
        header = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            padding=[dp(20), dp(10)],
            spacing=dp(10)
        )
        with header.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=header.pos, size=header.size, radius=[0, 0, dp(20), dp(20)])
        header.bind(pos=self._upd_header, size=self._upd_header)
        
        header.add_widget(Label(
            text='[b]Save Insta[/b]',
            markup=True,
            font_size='24sp',
            color=IOS_BLACK
        ))
        root.add_widget(header)

        # Content
        self.content = BoxLayout()
        root.add_widget(self.content)

        # Bottom Tab Bar (iOS Style)
        tab_bar = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(20), dp(10)],
            spacing=dp(30)
        )
        with tab_bar.canvas.before:
            Color(1, 1, 1, 0.95)
            self.tab_rect = RoundedRectangle(pos=tab_bar.pos, size=tab_bar.size, radius=[dp(20), dp(20), 0, 0])
        tab_bar.bind(pos=self._upd_tab, size=self._upd_tab)

        self.btn_search = self._tab_btn('🔍', 'بحث', True)
        self.btn_download = self._tab_btn('⬇️', 'تحميل', False)
        self.btn_about = self._tab_btn('©️', 'حول', False)

        self.btn_search.bind(on_press=lambda x: self.show_search())
        self.btn_download.bind(on_press=lambda x: self.show_download())
        self.btn_about.bind(on_press=lambda x: self.show_about())

        tab_bar.add_widget(Widget())
        tab_bar.add_widget(self.btn_search)
        tab_bar.add_widget(Widget())
        tab_bar.add_widget(self.btn_download)
        tab_bar.add_widget(Widget())
        tab_bar.add_widget(self.btn_about)
        tab_bar.add_widget(Widget())

        root.add_widget(tab_bar)

        self.show_search()
        return root

    def _upd_header(self, inst, val):
        inst.canvas.before.clear()
        with inst.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=inst.pos, size=inst.size, radius=[0, 0, dp(20), dp(20)])

    def _upd_tab(self, inst, val):
        inst.canvas.before.clear()
        with inst.canvas.before:
            Color(1, 1, 1, 0.95)
            RoundedRectangle(pos=inst.pos, size=inst.size, radius=[dp(20), dp(20), 0, 0])

    def _tab_btn(self, icon, label, active):
        box = BoxLayout(orientation='vertical', spacing=dp(2))
        color = IOS_BLUE if active else IOS_GRAY
        lbl = Label(text=icon, font_size='22sp', color=color, size_hint_y=None, height=dp(28))
        txt = Label(text=label, font_size='11sp', color=color, size_hint_y=None, height=dp(18))
        box.add_widget(lbl)
        box.add_widget(txt)
        box.lbl = lbl
        box.txt = txt
        return box

    def _set_active(self, active_btn):
        for btn in [self.btn_search, self.btn_download, self.btn_about]:
            btn.lbl.color = IOS_BLUE if btn == active_btn else IOS_GRAY
            btn.txt.color = IOS_BLUE if btn == active_btn else IOS_GRAY

    def show_search(self):
        self._set_active(self.btn_search)
        self.content.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(20))
        
        # Search Card
        card = iOSCard(orientation='vertical', spacing=dp(12))
        card.bind(minimum_height=card.setter('height'))
        
        card.add_widget(Label(
            text='🔍 بحث عن حساب',
            font_size='18sp',
            bold=True,
            color=IOS_BLACK,
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.search_input = iOSInput(hint_text='اسم المستخدم (بدون @)')
        card.add_widget(self.search_input)
        
        search_btn = iOSButton(text='بحث')
        search_btn.bind(on_press=self.do_search)
        card.add_widget(search_btn)
        
        layout.add_widget(card)
        layout.add_widget(Widget(size_hint_y=None, height=dp(10)))

        # Results
        self.result_container = BoxLayout(orientation='vertical', spacing=dp(12), size_hint_y=None)
        self.result_container.bind(minimum_height=self.result_container.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.result_container)
        layout.add_widget(scroll)
        
        self.content.add_widget(layout)

    def show_download(self):
        self._set_active(self.btn_download)
        self.content.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(20))
        
        card = iOSCard(orientation='vertical', spacing=dp(12))
        card.bind(minimum_height=card.setter('height'))
        
        card.add_widget(Label(
            text='⬇️ تحميل من رابط',
            font_size='18sp',
            bold=True,
            color=IOS_BLACK,
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.url_input = iOSInput(hint_text='ألصق رابط الريلز أو الستوري...')
        card.add_widget(self.url_input)
        
        dl_btn = iOSButton(text='تحميل الآن', background_color=IOS_GREEN)
        dl_btn.bind(on_press=self.do_download)
        card.add_widget(dl_btn)
        
        layout.add_widget(card)
        layout.add_widget(Widget(size_hint_y=None, height=dp(10)))

        self.dl_status = Label(
            text='',
            font_size='14sp',
            color=IOS_GRAY,
            size_hint_y=None,
            height=dp(100)
        )
        layout.add_widget(self.dl_status)
        
        self.content.add_widget(layout)

    def show_about(self):
        self._set_active(self.btn_about)
        self.content.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(30))
        
        layout.add_widget(Widget())
        
        # App Icon Placeholder
        icon_box = BoxLayout(size_hint_y=None, height=dp(100))
        with icon_box.canvas:
            Color(*IOS_BLUE)
            RoundedRectangle(pos=(Window.width/2 - dp(40), dp(10)), size=(dp(80), dp(80)), radius=[dp(20)]*4)
        icon_box.add_widget(Label(
            text='📱',
            font_size='40sp',
            size_hint_x=None,
            width=dp(80)
        ))
        layout.add_widget(icon_box)
        
        layout.add_widget(Label(
            text='[b]Save Insta[/b]',
            markup=True,
            font_size='28sp',
            color=IOS_BLACK
        ))
        layout.add_widget(Label(
            text='تحميل ريلزات وستوريات وبروفايل',
            font_size='14sp',
            color=IOS_GRAY
        ))
        layout.add_widget(Label(
            text='إنستغرام',
            font_size='14sp',
            color=IOS_GRAY
        ))
        
        layout.add_widget(Widget(size_hint_y=None, height=dp(30)))
        
        # Copyright Card
        card = iOSCard(orientation='vertical', spacing=dp(8))
        card.add_widget(Label(
            text='© 2026 Youssef Mansouri',
            font_size='16sp',
            bold=True,
            color=IOS_BLACK
        ))
        card.add_widget(Label(
            text='جميع الحقوق محفوظة',
            font_size='13sp',
            color=IOS_GRAY
        ))
        card.add_widget(Label(
            text='صُنع ب❤️ في المغرب',
            font_size='13sp',
            color=IOS_BLUE
        ))
        layout.add_widget(card)
        
        layout.add_widget(Widget())
        self.content.add_widget(layout)

    def do_search(self, instance):
        username = self.search_input.text.strip()
        if not username:
            self.show_popup('❌ أدخل اسم المستخدم')
            return
        self.result_container.clear_widgets()
        self.result_container.add_widget(Label(text='⏳ جاري البحث...', color=IOS_GRAY))
        threading.Thread(target=self._search_thread, args=(username,)).start()

    def _search_thread(self, username):
        result = scrape_profile(username)
        Clock.schedule_once(lambda dt: self._show_result(result), 0)

    def _show_result(self, result):
        self.result_container.clear_widgets()
        if result.get('error'):
            self.result_container.add_widget(Label(
                text=result['error'],
                color=IOS_RED,
                font_size='15sp'
            ))
        else:
            self.result_container.add_widget(ProfileCard(result))

    def do_download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.show_popup('❌ ألصق الرابط أولاً')
            return
        self.dl_status.text = '⏳ جاري التحميل...'
        self.dl_status.color = IOS_BLUE
        threading.Thread(target=self._dl_thread, args=(url,)).start()

    def _dl_thread(self, url):
        try:
            try:
                from android.storage import primary_external_storage_path
                base = primary_external_storage_path()
            except:
                base = os.path.expanduser("~")
            sd = os.path.join(base, "Download", "SaveInsta", f"dl_{int(time.time())}")
            files, err = download_media(url, sd)
            if err:
                Clock.schedule_once(lambda dt: self._set_dl_status(f'❌ {err}', IOS_RED), 0)
            else:
                names = '\n'.join([os.path.basename(f) for f in files])
                Clock.schedule_once(lambda dt: self._set_dl_status(f'✅ تم التحميل:\n{names}', IOS_GREEN), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._set_dl_status(f'❌ {str(e)[:100]}', IOS_RED), 0)

    def _set_dl_status(self, text, color):
        self.dl_status.text = text
        self.dl_status.color = color

    def show_popup(self, msg):
        popup = Popup(
            title='',
            content=Label(text=msg, font_size='16sp', color=IOS_WHITE),
            size_hint=(0.75, 0.15),
            background_color=(0, 0, 0, 0.85),
            separator_height=0
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2.5)

if __name__ == '__main__':
    SaveInstaApp().run()
