# Import necessary modules
import urllib.request
import io
import threading
import re
import os
import hashlib
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from PIL import Image
from datetime import datetime

# Setup global variables
CACHE_DIR = '/Applications/PhobosClient/cache/DiscordBotsAutofarm'
os.makedirs(CACHE_DIR, exist_ok=True)


def render_discord_message(dashboard, author_name, author_avatar_url, content, attachments=None, embeds=None):
    '''Dynamically renders incoming Discord chat events with sequential stacking layout.'''

    # Ensure the feed frame exists before attempting to render
    if not hasattr(dashboard, 'feed_frame') or not dashboard.feed_frame.winfo_exists():
        return

    # Clean up formatting strings from content
    if content:
        content = content.replace('**', '')

    # Set up the main message container
    msg_container = ctk.CTkFrame(dashboard.feed_frame, fg_color='transparent')
    msg_container.pack(fill='x', pady=6, padx=5, anchor='w')

    # Assign a safe name fallback
    safe_name = author_name if author_name else 'Unknown'

    # Set up the avatar frame
    avatar_frame = ctk.CTkFrame(msg_container, fg_color='transparent', width=40)
    avatar_frame.pack(side='left', anchor='n', padx=(0, 10))
    avatar_frame.pack_propagate(False)

    # Load default avatar label based on username
    avatar_label = ctk.CTkLabel(avatar_frame,
                                text='🤖' if any(x in safe_name.lower() for x in ['owo', 'fisher']) else '👤',
                                font=('Arial', 20), width=40, height=40)
    avatar_label.pack(fill='both', expand=True)

    # Load author avatar if available
    if author_avatar_url:
        def apply_avatar(img_obj, url):
            try:
                ctk_img = ctk.CTkImage(light_image=img_obj, dark_image=img_obj, size=(40, 40))
                avatar_label.configure(image=ctk_img, text='')
                dashboard.image_cache[url] = ctk_img
            except:
                pass

        def load_avatar():
            try:
                url_hash = hashlib.md5(author_avatar_url.encode('utf-8')).hexdigest()
                local_path = os.path.join(CACHE_DIR, f'avatar_{url_hash}.png')
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        img_data = f.read()
                else:
                    req = urllib.request.Request(author_avatar_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as r:
                        img_data = r.read()
                    with open(local_path, 'wb') as f:
                        f.write(img_data)
                img = Image.open(io.BytesIO(img_data)).resize((40, 40), Image.Resampling.LANCZOS)
                avatar_label.after(0, lambda: apply_avatar(img, author_avatar_url))
            except:
                pass

        # Run avatar loading in a background thread
        threading.Thread(target=load_avatar, daemon=True).start()

    # Setup the right content stack for text and media
    right_content_stack = ctk.CTkFrame(msg_container, fg_color='transparent')
    right_content_stack.pack(side='left', fill='x', expand=True, anchor='nw')

    # Setup meta frame for author name and timestamp
    meta_frame = ctk.CTkFrame(right_content_stack, fg_color='transparent')
    meta_frame.pack(fill='x', anchor='w', pady=(0, 2))

    # Determine author name color
    name_color = '#1f8b4c' if any(x in safe_name.lower() for x in ['owo', 'fisher']) else '#ffffff'
    ctk.CTkLabel(meta_frame, text=safe_name, font=('Arial', 13, 'bold'), text_color=name_color).pack(side='left')
    ctk.CTkLabel(meta_frame, text=datetime.now().strftime('Today at %I:%M:%S %p'), font=('Arial', 10),
                 text_color='#949ba4').pack(side='left', padx=10)

    # Setup fonts dynamically based on OS
    font_family = 'Segoe UI' if os.name == 'nt' else 'Helvetica'
    mono_family = 'Consolas' if os.name == 'nt' else 'Courier'
    base_font = tkfont.Font(family=font_family, size=11, weight='normal')
    code_font = tkfont.Font(family=mono_family, size=10, weight='normal')

    # Setup reusable rich text renderer
    def render_rich_text(parent_ui, text_string, bg_hex):
        text_container = ctk.CTkFrame(parent_ui, fg_color='transparent', width=560, height=24)
        text_container.pack(fill='x', anchor='nw', pady=(2, 2))
        text_container.pack_propagate(False)

        text_widget = tk.Text(text_container, bg=bg_hex, fg='#dbdee1', wrap='word', bd=0, highlightthickness=0)
        text_widget.pack(fill='both', expand=True)
        text_widget.configure(font=base_font)
        text_widget.tag_configure('code', font=code_font, background='#202225', foreground='#e3e5e8')

        # Split text into tokens for emojis and markdown
        tokens = re.split(r'(<a?:[^:]+:[0-9]+>)', text_string)

        def adjust_height_pixels(*args):
            try:
                text_widget.update_idletasks()
                pixel_measurement = text_widget.count('1.0', 'end', 'ypixels')
                if pixel_measurement and pixel_measurement[0] > 0:
                    calculated_h = pixel_measurement[0] + 8
                else:
                    lines = text_widget.count('1.0', 'end-1c', 'displaylines')
                    calculated_h = ((lines[0] if lines else 1) * 19) + 8

                text_container.configure(height=max(24, calculated_h))
                msg_container.update_idletasks()
                dashboard.feed_frame.update_idletasks()
                if hasattr(dashboard.feed_frame, '_parent_canvas'):
                    dashboard.feed_frame._parent_canvas.yview_moveto(1.0)
            except:
                pass

        # Process tokens
        for token in tokens:
            if not token: continue
            emoji_match = re.match(r'<a?:([^:]+):([0-9]+)>', token)
            if emoji_match:
                emoji_name, emoji_id = emoji_match.group(1), emoji_match.group(2)
                emoji_url = f'https://cdn.discordapp.com/emojis/{emoji_id}.png?size=24'
                emoji_lbl = ctk.CTkLabel(text_widget, text=f':{emoji_name}:', text_color='#dbdee1',
                                         fg_color=bg_hex, font=(font_family, 10))
                text_widget.window_create(tk.END, window=emoji_lbl, align='center')

                def apply_emoji(img_obj, lbl, url):
                    try:
                        ctk_img = ctk.CTkImage(light_image=img_obj, dark_image=img_obj, size=(20, 20))
                        lbl.configure(image=ctk_img, text='')
                        dashboard.image_cache[url] = ctk_img
                        text_widget.after(10, adjust_height_pixels)
                    except:
                        pass

                def load_emoji(url=emoji_url, lbl=emoji_lbl, eid=emoji_id):
                    try:
                        local_path = os.path.join(CACHE_DIR, f'emoji_{eid}.png')
                        if os.path.exists(local_path):
                            with open(local_path, 'rb') as f:
                                raw = f.read()
                        else:
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req) as r:
                                raw = r.read()
                            with open(local_path, 'wb') as f:
                                f.write(raw)
                        img = Image.open(io.BytesIO(raw)).resize((20, 20), Image.Resampling.LANCZOS)
                        lbl.after(0, lambda: apply_emoji(img, lbl, url))
                    except:
                        pass

                # Run emoji loading in a background thread
                threading.Thread(target=load_emoji, daemon=True).start()
            else:
                markdown_parts = re.split(r'(\`.*?\`)', token)
                for part in markdown_parts:
                    if not part: continue
                    if part.startswith('`') and part.endswith('`') and len(part) >= 2:
                        text_widget.insert(tk.END, part[1:-1], 'code')
                    else:
                        text_widget.insert(tk.END, part)

        # Finalize text widget configuration
        text_widget.config(state='disabled')
        text_widget.after(5, adjust_height_pixels)
        text_widget.after(50, adjust_height_pixels)
        text_widget.bind('<Configure>', lambda e: text_widget.after(10, adjust_height_pixels))

    # Process main content string
    if content and content.strip():
        render_rich_text(right_content_stack, content, '#313338')

    # Process message embeds
    if embeds:
        for embed in embeds:
            embed_card = ctk.CTkFrame(right_content_stack, fg_color='#1e1f22', corner_radius=4)
            embed_card.pack(fill='x', anchor='w', pady=4, padx=(0, 20))

            accent_bar = ctk.CTkFrame(embed_card, fg_color='#248046', width=4)
            accent_bar.pack(side='left', fill='y')

            embed_body = ctk.CTkFrame(embed_card, fg_color='transparent')
            embed_body.pack(side='left', fill='both', expand=True, padx=12, pady=10)

            if 'title' in embed and embed['title']:
                ctk.CTkLabel(embed_body, text=embed['title'].replace('**', ''), font=(font_family, 13, 'bold'),
                             text_color='#ffffff', anchor='w').pack(fill='x', pady=(0, 4))

            if 'description' in embed and embed['description']:
                render_rich_text(embed_body, embed['description'].replace('**', ''), '#1e1f22')

            def render_embed_graphic(img_url):
                if not img_url: return
                embed_img_label = ctk.CTkLabel(embed_body, text='[Loading Embedded Image...]', text_color='#58a6ff')
                embed_img_label.pack(anchor='w', pady=6)

                def apply_embed_image(img_obj, label, url, w, h):
                    try:
                        ctk_img = ctk.CTkImage(light_image=img_obj, dark_image=img_obj, size=(w, h))
                        label.configure(image=ctk_img, text='')
                        dashboard.image_cache[url] = ctk_img
                        if hasattr(dashboard.feed_frame, '_parent_canvas'):
                            dashboard.feed_frame._parent_canvas.yview_moveto(1.0)
                    except:
                        label.pack_forget()

                def load_embed_image(url=img_url, label=embed_img_label):
                    try:
                        # Fetch the image directly into memory without saving to disk
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as r:
                            raw_data = r.read()

                        img = Image.open(io.BytesIO(raw_data))
                        base_width = min(400, img.size[0])
                        w_percent = (base_width / float(img.size[0]))
                        h_size = int((float(img.size[1]) * float(w_percent)))
                        img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

                        label.after(0, lambda: apply_embed_image(img, label, url, base_width, h_size))
                    except:
                        label.after(0, lambda: label.pack_forget())

                # Run embed graphic loading in a background thread
                threading.Thread(target=load_embed_image, daemon=True).start()

            if 'image' in embed and isinstance(embed['image'], dict):
                render_embed_graphic(embed['image'].get('url'))
            if 'thumbnail' in embed and isinstance(embed['thumbnail'], dict):
                render_embed_graphic(embed['thumbnail'].get('url'))

    # Process media attachments
    if attachments:
        for attach_url in attachments:
            if any(ext in attach_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                media_placeholder = ctk.CTkLabel(right_content_stack, text='[Loading Attachment...]',
                                                 text_color='#58a6ff')
                media_placeholder.pack(anchor='w', pady=4)

                def apply_attachment(img_obj, label, url, w, h):
                    try:
                        ctk_img = ctk.CTkImage(light_image=img_obj, dark_image=img_obj, size=(w, h))
                        label.configure(image=ctk_img, text='')
                        dashboard.image_cache[url] = ctk_img
                        if hasattr(dashboard.feed_frame, '_parent_canvas'):
                            dashboard.feed_frame._parent_canvas.yview_moveto(1.0)
                    except:
                        label.configure(text='[Image Failed to Render]')

                def load_attachment(url=attach_url, label=media_placeholder):
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as r:
                            raw_data = r.read()
                        img = Image.open(io.BytesIO(raw_data))
                        base_width = 300
                        w_percent = (base_width / float(img.size[0]))
                        h_size = int((float(img.size[1]) * float(w_percent)))
                        img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
                        label.after(0, lambda: apply_attachment(img, label, url, base_width, h_size))
                    except:
                        label.after(0, lambda: label.configure(text='[Image Failed to Load]'))

                # Run media attachment loading in a background thread
                threading.Thread(target=load_attachment, daemon=True).start()

    # Move scrollbar to bottom
    if hasattr(dashboard.feed_frame, '_parent_canvas'):
        dashboard.feed_frame._parent_canvas.yview_moveto(1.0)
