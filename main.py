#!/usr/bin/python3
import gi, os, json, marshal
for a, b in (("Soup", "3.0"), ("Gtk", "4.0"), ("Adw", "1"), ("Gly", "2"), ("GlyGtk4", "2"), ("AppStream", "1.0")): gi.require_version(a, b)
from gi.repository import AppStream, Gio, GLib, Gtk, Adw, Gdk, Gly, GlyGtk4, Soup
from MasonryBox import MasonryBox
from PaintableColorThief import palette
from TagRow import TagRow
com = (m := AppStream.Metadata(), m.parse_file(Gio.File.new_for_path(os.path.join(GLib.get_system_data_dirs()[0], "metainfo", "io.github.kirukomaru11.Cardboard.metainfo.xml")), 1), m.get_component())[-1]
Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(os.path.join(GLib.get_system_data_dirs()[0], com.props.id))
(s := Gtk.CssProvider.new(), s.load_from_path(os.path.join(GLib.get_system_data_dirs()[0], com.props.id, "style.css")), Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), s, 800))
app = Adw.Application(application_id=com.props.id)
app.register()
(app.run(), exit()) if app.props.is_remote else None
file_launcher, uri_launcher = Gtk.FileLauncher.new(), Gtk.UriLauncher.new()
Action = lambda n, s, c: (a := Gio.SimpleAction.new(n, None), app.add_action(a), app.set_accels_for_action(f"app.{n}", s), a.connect("activate", c))
shortcuts, about = Adw.ShortcutsDialog(), Adw.AboutDialog(application_icon=f"{com.props.id}-symbolic", application_name=com.props.name, developer_name=com.get_developer().get_name(), issue_url=tuple(com.props.urls.values())[0], website=tuple(com.props.urls.values())[-1], license_type=7, version=com.get_releases_plain().get_entries()[0].get_version(), release_notes=com.get_releases_plain().get_entries()[0].get_description())
Action("about", (), lambda *_: about.present(app.props.active_window))
Action("shortcuts", ("<primary>question",), lambda *_: shortcuts.present(app.props.active_window))
general, tabs = tuple(Adw.ShortcutsSection(title=i) for i in ("General", "Tabs"))
for t, a in (("Add File", "<primary><shift>a"), ("Add URL", "<primary><shift>d"), ("Paste File/Image/URL", "<primary>v"), ("Keyboard Shortcuts", "<primary>question"), ("Preferences", "<primary>p"), ("Fullscreen", "F11")): general.add(Adw.ShortcutsItem(title=t, accelerator=a))
for t, a in (("Overview", "<primary><shift>o"), ("Open in Browser", "<primary>o"), ("New Tab", "<primary>t"), ("Close Tab", "<primary>w"), ("Reopen Closed Tab", "<primary><shift>t"), ("Toggle Favorite/Bookmark", "<primary>d"), ("Toggle Constrain", "<primary>f"), ("Edit Post", "<primary>e"), ("Download Post", "<primary>s")): tabs.add(Adw.ShortcutsItem(title=t, accelerator=a))
for t, a in (("Next Tab", "<primary>Tab <primary>Page_Down"), ("Previous Tab", "<primary><shift>Tab <primary>Page_Up"), ("First Tab", "<primary>Home"), ("Last Tab", "<primary>End"), ("Move Tab Forward", "<primary><shift>Page_Down"), ("Move Tab Backward", "<primary><shift>Page_Up"), ("Move Tab to Start", "<primary><shift>Home"), ("Move Tab to End", "<primary><shift>End"), ("Switch to Tabs 1-9", "<alt>1...9"), ("Switch to Tab 10", "<alt>0")): tabs.add(Adw.ShortcutsItem(title=t, accelerator=a))
for i in (general, tabs): shortcuts.add(i)
def Button(t="button", callback=None, icon_name="", bindings=(), **kargs):
    bt = Gtk.MenuButton if t == "menu" else Gtk.ToggleButton if t == "toggle" else Gtk.Button
    bt = bt(icon_name=icon_name + "-symbolic" if icon_name else "", **kargs)
    if callback: bt.connect("clicked" if t == "button" else "notify::active", callback)
    for b in bindings:
        source = b[0] if b[0] else bt
        source.bind_property(b[1], b[2] if b[2] else bt, b[3], b[4] if len(b) >= 5 and b[4] else 0 | 2, b[5] if len(b) >= 6 else None)
    return bt

menus = tuple(Gio.Menu.new() for _ in range(4))
for n, i in enumerate(((("Add a URL", "add-url"), ("Add Files to Favorites", "add-file")),
                    (("View Open Tabs", "overview"), ("Reopen Closed Tab", "reopen-tab"), ("Fullscreen", "fullscreen")),
                    (("Preferences", "preferences"), ("Keyboard Shortcuts", "shortcuts"), (f"About {about.props.application_name}", "about")))):
    for t, a in i: menus[n].append(t, "app." + a)
for i in menus[:3]: (i.freeze(), menus[3].append_section(None, i))
menus[3].freeze()

app_data, session = Gio.File.new_for_path(os.path.join(GLib.get_user_data_dir(), about.props.application_name.lower())), Soup.Session(user_agent=about.props.application_name, max_conns_per_host=10)
limit, ratings = 30, ("General", "Sensitive", "Questionable", "Explicit")
sites = {"Favorites": {
        "url": app_data.get_uri(),
        "get_url": lambda q: app_data,
        "overrides": {
            "size": lambda p: f"{p['width']}x{p['height']} ({GLib.format_size(p['size'])})",
            "duration": lambda p: GLib.DateTime.new_from_unix_utc(p["duration"]).format("%T") if p["duration"] > 0 else None,
            "created_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["created_at"]), lambda d: d.to_utc().to_unix()),
            "updated_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["updated_at"]), lambda d: d.to_utc().to_unix()),},},
        "Danbooru": {"url": "https://danbooru.donmai.us",
                     "api": lambda: f"&api_key={prefs['Danbooru > Token'].props.text}&login={prefs['Danbooru > User'].props.text}" if prefs["Danbooru > User"].props.text and prefs["Danbooru > Token"].props.text else ""},
        "Gelbooru": {"url": "https://gelbooru.com",
                     "api": lambda: f"&api_key={prefs['Gelbooru > Token'].props.text}&user_id={prefs['Gelbooru > User'].props.text}" if prefs["Gelbooru > User"].props.text and prefs["Gelbooru > Token"].props.text else ""},
        "AI Booru": {"url": "https://aibooru.ovh",},
        "Yande.re": {"url": "https://yande.re",},
        "Konachan": {"url": "https://konachan.com",},
        "Sakugabooru": {"url": "https://sakugabooru.com",}
        }

def get_property(o, k, s):
    if " || " in k:
        k = k.split(" || ")[0]
    if k in sites[s]["overrides"]:
        if callable(sites[s]["overrides"][k]): return sites[s]["overrides"][k](o)
        if callable(sites[s]["overrides"][k][0]): return sites[s]["overrides"][k][0](o)
        return sites[s]["overrides"][k]
    if k in o: return o[k]
def fetch_favorite_catalog(queries):
    catalog = []
    queries, s = " ".join(tuple(i for i in queries.split(" ") if not i.lower().startswith("order:"))).split("+"), tuple(i for i in queries.split(" ") if i.lower().startswith("order:"))
    s = s[0].lower().split(":")[1] if s else "added"
    for query in queries:
        terms = tuple(i for i in query.split(" ") if i and not i.startswith(("-site:", "site:")))
        key_terms = tuple(i for i in terms if ":" in i and len(i.split(":")) == 2)
        terms = tuple(i for i in terms if not i in key_terms)
        key_terms = tuple(i.split(":") for i in key_terms)
        term_sites = [i.replace("_", " ") for i in query.split(" ") if i.startswith(("-site:", "site:"))]
        if not tuple(i for i in term_sites if i.startswith("site:")):
            term_sites += [i for i in sites if not tuple(it for it in term_sites if it.split(":")[-1] == i)]
        term_sites = tuple(i.split(":")[-1] for i in term_sites if not i.startswith("-") and i.split(":")[-1] in app.data[0])
        for site in term_sites:
            for p in app.data[0][site]:
                if not "added" in p:
                    p["added"] = GLib.DateTime.new_now_utc().to_unix()
                if prefs["View > Safe Mode"].props.active and not 1 > get_property(p, "rating", site): continue
                if any(t[:1] in get_property(p, "tags", site) for t in terms if t.startswith("-")): continue
                if not all(t in get_property(p, "tags", site) for t in terms): continue
                if any(not k[0] in p or str(get_property(p, k[0], site)) != k[1] for k in key_terms): continue
                catalog.append((p, site))
    if "random" in s:
        k = lambda c: GLib.random_int()
    else:
        k = lambda c: (v := get_property(c[0], s.split("_asc")[0], c[1]), v if v else c[0]["id"])[-1]
    catalog.sort(key=k, reverse=not "_asc" in s)
    return catalog
    
def fetch_online_catalog(site, queries, page, count=False):
    catalog = [0, []]
    for query in queries.split("+"):
        response = json.loads(session.send_and_read(Soup.Message.new("GET", sites[site]["fetch_catalog"](query, page))).get_data().decode("utf-8"))
        if count:
            n = response
            if "fetch_count" in sites[site]:
                n = session.send_and_read(Soup.Message.new("GET", sites[site]["fetch_count"](query))).get_data().decode("utf-8")
            if "get_count" in sites[site]:
                n = sites[site]["get_count"]((n, response))
            catalog[0] += n
        catalog[1] += sites[site]["get_catalog"](response) if "get_catalog" in sites[site] else response
    if "+" in queries: catalog[1].sort(key=lambda i: i["id"], reverse=True)
    return catalog
def finish_adding_post(s, r, st):
    b = s.send_and_read_finish(r)
    if not b:
        return toast_overlay.add_toast(Adw.Toast(title=f"Couldn't add {url}! Status: {r.get_status()}", use_markup=False))
    p = json.loads(b.get_data().decode("utf-8"))
    p = p["post"] if "post" and "@attributes" in p else p
    p = p[0] if isinstance(p, list) else p
    if not "file_url" in p or "file_url" in sites[st]["overrides"] and not sites[st]["overrides"]["file_url"][0](p):
        return toast_overlay.add_toast(Adw.Toast(title=f"Couldn't add {url}: File URL not in post!", use_markup=False))
    p["added"] = GLib.DateTime.new_now_utc().to_unix()
    app.data[0][st].append(p)
    toast_overlay.add_toast(Adw.Toast(title=f"{p['id']} added to {st}'s favorites"))
def general_add(url):
    if "?" in url and "tags=" in url:
        tags = GLib.Uri.parse_params(url.split("?")[-1], -1, "&", 0)["tags"].replace("+", " ")
        if tags in prefs["Bookmarks"].tags:
            toast_overlay.add_toast(Adw.Toast(title=f"{tags} already in bookmarks!"))
        else:
            prefs["Bookmarks"].tags += [tags]
            toast_overlay.add_toast(Adw.Toast(title=f"{tags} added to bookmarks"))
    else:
        toast_overlay.add_toast(Adw.Toast(title=f"Couldn't add {url}", use_markup=False))
def danbooru_add(s, url):
    if "/posts/" in url:
        p_id = url.split("?")[0].split("/posts/")[-1]
        if [i for i in app.data[0][s] if i["id"] == p_id]:
            return toast_overlay.add_toast(Adw.Toast(title=f"{p_id} already in {s}'s favorites!", timeout=0))
        r = session.send_and_read_async(Soup.Message.new("GET", f"{url.split('?')[0]}.json"), GLib.PRIORITY_DEFAULT, None, finish_adding_post, s)
    else:
        general_add(url)
def gelbooru_add(s, url):
    if "id=" in url:
        p_id = GLib.Uri.parse_params(url.split("?")[-1], -1, "&", 0)["id"]
        if [i for i in app.data[0][s] if i["id"] == p_id]:
            return toast_overlay.add_toast(Adw.Toast(title=f"{p_id} already in {s}'s favorites!"))
        r = session.send_and_read_async(Soup.Message.new("GET", sites[s]["fetch_catalog"](f"id:{p_id}", 1)), GLib.PRIORITY_DEFAULT, None, finish_adding_post, s)
    else:
        general_add(url)
def moebooru_add(s, url):
    if "/post/show/" in url:
        p_id = url.split("?")[0].split("/post/show/")[-1].split("/")[0]
        if [i for i in app.data[0][s] if i["id"] == p_id]:
            return toast_overlay.add_toast(Adw.Toast(title=f"{p_id} already in {s}'s favorites!", timeout=0))
        r = session.send_and_read_async(Soup.Message.new("GET", sites[s]["fetch_catalog"](f"id:{p_id}", 1)), GLib.PRIORITY_DEFAULT, None, finish_adding_post, s)
    else:
        general_add(url)

for i in ("Danbooru", "AI Booru"):
    sites[i]["add"] = danbooru_add
    sites[i]["fetch_catalog"] = lambda t, p, _i=i: f"{sites[_i]['url']}/posts.json?limit={limit}&page={p}&tags={t + (' status:any' if not 'status:' in t else '' + ' rating:safe' if prefs["View > Safe Mode"].props.active else '')}" + (sites[_i]["api"]() if "api" in sites[_i] else "")
    sites[i]["get_catalog"] = lambda c: tuple(i for i in c if "file_url" in i and not i["file_url"].endswith("swf"))
    sites[i]["fetch_count"] = lambda t, _i=i: f"{sites[_i]['url']}/counts/posts.json?tags={t}"
    sites[i]["get_count"] = lambda d: (c := json.loads(d[0]), c["counts"]["posts"] if c["counts"]["posts"] else 0)[1]
    sites[i]["get_url"] = lambda q, _i=i: f"{sites[_i]['url']}/posts/{q[0]['id']}" if isinstance(q[0], dict) else f"{sites[_i]['url']}/posts?page={q[1]}&tags={q[0] + (' status:any' if not 'status:' in q[0] else '') + (' rating:safe' if prefs["View > Safe Mode"].props.active else '')}"
    sites[i]["overrides"] = {
        "hash": lambda p: p["md5"],
        "rating": (lambda p: ratings.index(next(i for i in ratings if i.lower().startswith(p["rating"]))), lambda n: ratings[n].lower()[:1]),
        "duration": lambda p: GLib.DateTime.new_from_unix_utc(p["media_asset"]["duration"]).format("%T") if "media_asset" in p and "duration" in p["media_asset"] and p["media_asset"]["duration"] else None,
        "tags": (lambda p: p["tag_string"].split(" "), lambda t: " ".join(sorted(t))),
        "width": lambda p: p["image_width"],
        "height": lambda p: p["image_height"],
        "preview_url": (lambda p: p["preview_file_url"].replace("180x180", "720x720").replace(".jpg" if "/180x180/" in p["preview_file_url"] else ".webp", ".webp"), None),
        "parent_id": (lambda p: 0 if p["parent_id"] is None else p["parent_id"], lambda v: None if int(v) == 0 else int(v)),
        "uploader": lambda p: f"user_{p['uploader_id']}",
        "size": lambda p: f"{p['image_width']}x{p['image_height']} ({GLib.format_size(p['file_size'])})",
        "file_url": (lambda p: "" if not "file_url" in p else p["large_file_url"] if p["file_url"].endswith("zip") else p["file_url"], None),
        "created_at": (lambda p: GLib.DateTime.new_from_iso8601(p["created_at"]), lambda d: d.format_iso8601()),
        "updated_at": (lambda p: GLib.DateTime.new_from_iso8601(p["updated_at"]), lambda d: d.format_iso8601()),
    }
for i in ("Gelbooru",):
    sites[i]["add"] = gelbooru_add
    sites[i]["fetch_catalog"] = lambda t, p, _i=i: f"{sites[_i]['url']}/index.php?limit={limit}&pid={p - 1}&page=dapi&s=post&q=index&tags={t + (' rating:general' if prefs["View > Safe Mode"].props.active else '')}&json=1" + (sites[_i]["api"]() if "api" in sites[_i] else "")
    sites[i]["get_catalog"] = lambda c: c["post"] if "post" in c else []
    sites[i]["get_count"] = lambda c: c[1]["@attributes"]["count"]
    sites[i]["get_url"] = lambda q, _i=i: f"{sites[_i]['url']}/index.php?page=post&s=view&id={q[0]['id']}" if isinstance(q[0], dict) else f"{sites[_i]['url']}/index.php?page=post&s=list&pid={q[1] - 1}&tags={q[0] + (' rating:general' if prefs["View > Safe Mode"].props.active else '')}"
    sites[i]["overrides"] = {
        "hash": lambda p: p["md5"],
        "size": lambda p: f"{p['width']}x{p['height']}",
        "uploader": lambda p: p["owner"],
        "tags": (lambda p: p["tags"].split(" "), lambda t: " ".join(t)),
        "rating": (lambda p: ratings.index(p["rating"].title()), lambda r: ratings[r].lower()),
        "has_children": (lambda p: p["has_children"] == "true", lambda v: str(v).lower()),
        "created_at": (lambda p: (d := p["created_at"].rsplit(" ", 2), t := d.pop(1), da := Soup.date_time_new_from_http_string(" ".join(d)).format_iso8601().replace("Z", t), GLib.DateTime.new_from_iso8601(da))[-1], lambda d: d.format("%a %b %d %H:%M:%S %z %Y")),
        "updated_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["change"]), lambda d: d.to_utc().to_unix()),
    }
for i in ("Yande.re", "Konachan", "Sakugabooru"):
    sites[i]["add"] = moebooru_add
    sites[i]["fetch_catalog"] = lambda t, p, _i=i: f"{sites[_i]['url']}/post.json?limit={limit}&page={p}&tags={t + (' rating:general' if prefs["View > Safe Mode"].props.active else '')}&json=1" + (sites[_i]["api"]() if "api" in sites[_i] else "")
    sites[i]["get_catalog"] = lambda c: c[1]
    sites[i]["fetch_count"] = lambda t, _i=i: f"{sites[_i]['url']}/post.xml?tags={t}"
    sites[i]["get_count"] = lambda c: int(c[0].split('<posts count="')[1].split(' offset="')[0].strip('"'))
    sites[i]["get_url"] = lambda q, _i=i: f"{sites[_i]['url']}/post?id={q[0]['id']}" if isinstance(q[0], dict) else f"{sites[_i]['url']}/post?page={q[1]}&tags={q[0] + (' rating:general' if prefs["View > Safe Mode"].props.active else '')}"
    sites[i]["overrides"] = {
        "hash": lambda p: p["md5"],
        "size": lambda p: f"{p['width']}x{p['height']} ({GLib.format_size(p['file_size'])})",
        "uploader": lambda p: p["author"],
        "tags": (lambda p: p["tags"].split(" "), lambda t: " ".join(t)),
        "rating": (lambda p: ratings.index(next(i for i in ratings if i.lower().startswith(p["rating"]))), lambda n: ratings[n].lower()[:1]),
        "parent_id": (lambda p: 0 if p["parent_id"] is None else p["parent_id"], lambda v: None if int(v) == 0 else int(v)),
        "created_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["created_at"]), lambda d: d.to_utc().to_unix()),
    }

get_md5 = lambda b: (c := GLib.Checksum.new(0), c.update(b.get_data()), c.get_string())[-1]
def probe(url):
    p = Gio.Subprocess.new(("ffprobe", "-v", "quiet", "-show_entries", "stream=width,height:format=size,duration", "-of", "json", "-i", url), Gio.SubprocessFlags.STDOUT_PIPE)
    p.wait()
    try:
        o = json.loads(p.get_stdout_pipe().read_bytes(8192).get_data())
        if not "streams" in o: return print(f"No valid stream in {url}")
        i = o["streams"][0]
        i["duration"] = int(float(o["format"].get("duration", 0)))
        i["size"] = int(o["format"].get("size", 0))
        i["file_url"] = url
        return i
    except Exception as e: return print(f"URL: {url}\nError: {e}")
def add_favorite(p):
    now = GLib.DateTime.new_now_utc().to_unix()
    for k, v in (("id", max((i["id"] for i in app.data[0]["Favorites"]), default=0) + 1), ("width", 0), ("height", 0), ("duration", 0), ("rating", 0), ("source", ""), ("has_children", False), ("parent_id", 0), ("tags", []), ("added", now), ("created_at", now), ("updated_at", now), ("file_url", ""), ("preview_url", ""), ("hash", ""), ("size", 0)): p.setdefault(k, v)
    if not p["file_url"].startswith("http"):
        p["file_url"] = f"file://{p['file_url']}"
    app.data[0]["Favorites"].append(p)
    GLib.idle_add(toast_overlay.add_toast, Adw.Toast(title=f"Post {p['id']} added to favorites!"))
    return p
def fail_url(url, e=False):
    message = f"{url}\nError: {e}" if e else f"\n{url} could not be added!"
    print(message)
    return toast_overlay.add_toast(Adw.Toast(title=message, use_markup=False))
def add_from_url(s, r, fun, url):
    b = s.send_and_read_finish(r)
    if not b: fail_url(url)
    try: fun(b, url)
    except Exception as e: fail_url(url, e)
def zerochan_add(b, url):
    p = json.loads(b.get_data().decode("utf-8"))
    p["source"] = p["source"] if "source" in p else url
    p["file_url"], p["preview_url"] = p["full"], p["medium"]
    for i in ("primary", "small", "medium", "large", "full", "id"): del p[i]
    add_favorite(p)
def twitter_add(b, url):
    medias = []
    if "/status/" in url:
        h = b.get_data().decode("utf-8")
        h = h.split('"main-tweet"')[1].split('"attachments"')[1].split("</div></div>")[0]
        for r in h.split('"gallery-row"'):
            for i in r.split('href="'):
                if not "/pic/orig/" in i: continue
                medias.append(i.split('"')[0].split("%2F")[1])
    else:
        if "pbs.twimg.com" in url and "format=" in url:
            i = f'{url.split("/")[-1].split("?")[0]}.{url.split("format=")[1].split("&")[0]}' 
        elif "pbs.twimg.com" in url:
            i = url.split("/")[-1].split("?")[0] 
        else:
            i = url.split("%2F")[1]
        medias.append(i)
    for i in medias:
        file_url = f'https://pbs.twimg.com/media/{i.split(".")[0]}?format={i.split(".")[-1].split("%")[0]}&name=orig'
        p = probe(file_url)
        p["source"] = url.replace("nitter.net", "x.com") if "/status/" in url else file_url
        p["preview_url"] = file_url.replace("orig", "small")
        p["hash"] = get_md5(session.send_and_read(Soup.Message.new("GET", file_url)))
        add_favorite(p)
def chan_add(b, url):
    if "warosu" in url:
        response = b.get_data().decode("utf-8")
        p = url.rsplit("/", 1)[-1].split("#p")[-1]
        file_url = response.split(f"alt={p}")[0].rsplit("href=", 1)[1].split(">")[0]
        thumbnail_url = file_url.replace("img", "thumb").rsplit("/", 1)[0] + "/" + file_url.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "s.jpg"
        b = session.send_and_read(Soup.Message.new("GET", file_url))
    else:
        file_url = url.replace("thumb", "image").replace("s.", ".")
        thumbnail_url = file_url.replace("image", "thumb").rsplit("/", 1)[0] + "/" + file_url.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "s.jpg"
    p = probe(file_url)
    p["hash"], p["source"], p["preview_url"], p["created_at"] = get_md5(b), url, thumbnail_url, int(file_url.rsplit("/", 1)[-1].split(".")[0][:10])
    add_favorite(p)
def artstation_add(b, url):
    res = json.loads(b.get_data().decode("utf-8"))
    created_at, updated_at = GLib.DateTime.new_from_iso8601(res["created_at"]).to_utc().to_unix(), GLib.DateTime.new_from_iso8601(res["updated_at"]).to_utc().to_unix()
    tags = res["tags"] + res["title"].split(" ") + res["user"]["username"].split(" ")
    for i in res["assets"]:
        file_url = i["image_url"]
        for it in ("/small/", "/large/", "/medium/"):
            file_url = file_url.replace(it, "/4k/")
        p = probe(file_url)
        b = session.send_and_read(Soup.Message.new("GET", file_url))
        p["hash"], p["source"], p["preview_url"], p["created_at"], p["updated_at"], p["tags"] = get_md5(b), url, file_url.replace("/4k/", "/small/"), created_at, updated_at, tags
        add_favorite(p)
def reddit_add(b, url):
    res, to_add = b.get_data().decode("utf-8"), []
    if "<gallery-carousel style=" in res:
        for i in res.split("<gallery-carousel style=")[1].split('src="'):
            if i.startswith("https://preview.redd.it/"):
                i = f"https://i.redd.it/{i.split('?')[0].rsplit('-', 1)[1   ]}"
                if not i in to_add: to_add.append(i)
    else:
        to_add.append(res.rsplit("i18n-post-media-img", 1)[1].split('src="')[1].split('"')[0])
    for i in to_add:
        p = probe(i)
        b = session.send_and_read(Soup.Message.new("GET", i))
        p["hash"], p["source"], p["preview_url"] = get_md5(b), url, i
        add_favorite(p)
def pinterest_add(b, url):
    res = b.get_data().decode("utf-8")
    file_url = res.split('"ImageDetails","url":"')[1].split('"')[0]
    thumbnail_url = file_url.replace("originals", "1200x")
    p = probe(file_url)
    p["hash"], p["source"], p["preview_url"] = file_url.split("/")[-1].split(".")[0], url, thumbnail_url
    add_favorite(p)
def kemono_add(b, url):
    post = json.loads(b.get_data().decode("utf-8"))
    created_at, updated_at = tuple(GLib.DateTime.new_from_iso8601(post["post"][i], GLib.TimeZone.new_utc()) for i in ("published", "edited"))
    for i in post["previews"]:
        if not Gio.content_type_guess(i["name"])[0].startswith(("video", "image")): continue
        file_url = f'{i["server"]}/data{i["path"]}'
        p = probe(file_url)
        p["hash"], p["source"], p["preview_url"] = i["path"].split("/")[-1].split(".")[0], url, f'https://img.kemono.cr/thumbnail/data{i["path"]}'
        add_favorite(p)
extra = {"Zerochan": (lambda u: u.startswith("https://www.zerochan.net/") and u.split("/")[-1].isdigit(), lambda u: session.send_and_read_async(Soup.Message.new("GET", f"{u}?&json"), GLib.PRIORITY_DEFAULT, None, add_from_url, *(zerochan_add, u))),
        "Twitter": (lambda u: u.replace("https://", "").startswith(("xcancel.com", "twitter.com", "x.com", "nitter.net", "cdn.xcancel.com", "pbs.twimg.com")), lambda u: (url := u.replace("x.com", "nitter.net").replace("xcancel.com", "nitter.net").replace("twitter.com", "nitter.net"), session.send_and_read_async((m := Soup.Message.new("GET", url), tuple(m.props.request_headers.append(k, v) for k, v in (("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"), ("Accept-Language", "en-US,en;q=0.5"), ("Sec-Fetch-Dest", "document"))), m)[-1], GLib.PRIORITY_DEFAULT, None, add_from_url, *(twitter_add, url)))),
        "4chan": (lambda u: u.replace("https://", "").startswith(("boards.4chan.org", "warosu.org", "desu-usergeneratedcontent.xyz")), lambda u: (url := u.replace("boards.4chan", "warosu") if "boards.4chan" in u and u.split("/")[3].startswith(("3", "biz", "cgl", "ck", "diy", "fa", "ic", "jp", "lit", "sci", "vr", "vt")) else u, session.send_and_read_async(Soup.Message.new("GET", url), GLib.PRIORITY_DEFAULT, None, add_from_url, *(chan_add, url)))),
        "Artstation": (lambda u: "artstation.com/artwork/" in u, lambda u: session.send_and_read_async(Soup.Message.new("GET", f"{u.replace('artwork', 'projects')}.json"), GLib.PRIORITY_DEFAULT, None, add_from_url, *(artstation_add, u))),
        "Reddit": (lambda u: u.startswith("https://www.reddit.com/r/") and "/comments/" in u, lambda u: session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, add_from_url, *(reddit_add, u))),
        "Pinterest": (lambda u: "pinterest.com/pin/" in u, lambda u: session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, add_from_url, *(pinterest_add, u))),
        "Kemono": (lambda u: u.startswith("https://kemono.cr") and "user" in u and "post" in u, lambda u: session.send_and_read_async((m := Soup.Message.new("GET", u.replace(".cr", ".cr/api/v1/")), m.props.request_headers.append("Accept", "text/css"), m)[-1], GLib.PRIORITY_DEFAULT, None, add_from_url, *(kemono_add, u))),
        }
def add(v):
    if isinstance(v, str):
        for url in v.split("\n"):
            url = url.strip()
            if url.startswith("https://safebooru.donmai.us"):
                url = url.replace("https://safebooru.donmai.us", sites["Danbooru"]["url"])
            if url.startswith("https://danbooru.donmai.us"):
                url = url.replace("/post/show/", "/posts/")
            u = False
            for k in sites:
                if url.startswith(sites[k]["url"]):
                    sites[k]["add"](k, url)
                    u = True
                    continue
            for k in extra:
                if extra[k][0](url):
                    extra[k][1](url)
                    u = True
                    continue
            if u: continue
            try:
                p = probe(url)
                if not p: return fail_url(url)
                b = session.send_and_read(Soup.Message.new("GET", url))
                p["hash"], p["source"], p["preview_url"] = get_md5(b), url, url
                add_favorite(p)
                continue
            except Exception as e:
                fail_url(url, e)
                continue
            fail_url(url)
    if isinstance(v, Gdk.Texture):
        f, md5 = app_data.get_child(f"{md5}.png"), get_md5(v.save_to_png_bytes())
        v.save_to_png(f.peek_path())
        return add(Gdk.FileList.new_from_list((f,)))
    if isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            if not Gio.content_type_guess(file.get_basename())[0].startswith(("video", "image")):
                fail_url(file.peek_path())
                continue
            b = file.load_bytes()[0]
            md5 = get_md5(b)
            f, pr = app_data.get_child(f"{md5}.{file.peek_path().split('.')[-1]}"), app_data.get_child(f"preview-{md5}.webp")
            p = probe(file.peek_path())
            if not p: return fail_url(file.peek_path())
            Gio.Subprocess.new(("ffmpeg", "-v", "quiet", "-i", file.peek_path(), "-vf", r"thumbnail,scale=if(gte(iw\,ih)\,min(720\,iw)\,-2):if(lt(iw\,ih)\,min(720\,ih)\,-2)", "-frames:v", "1", pr.peek_path()), 0).wait()
            if not f.equal(file): file.copy(f, 0)
            p["hash"], p["source"], p["file_url"], p["preview_url"] = md5, file.get_uri(), f.get_uri(), pr.get_uri()
            add_favorite(p)
Action("add-file", ("<primary><shift>a",), lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.props.active_window, None, lambda d, r: add(d.open_multiple_finish(r))))
add_url = Adw.AlertDialog(heading="Add URL to Bookmarks/Favorites", css_classes=("alert", "floating", "addurl-dialog",), default_response="cancel", extra_child=Gtk.TextView(input_purpose=5))
add_url.connect("response", lambda d, r: add(add_url.props.extra_child.props.buffer.props.text) if r == "add" else None)
for i in ("cancel", "add"): add_url.add_response(i, i.title())
add_url.set_response_appearance("add", 1)
Action("add-url", ("<primary><shift>d",), lambda *_: (add_url.props.extra_child.props.buffer.set_text(""), add_url.present(app.props.active_window)))

search_popover = Gtk.Popover(child=Gtk.ListBox(selection_mode=0, css_classes=["boxed-list"]))
site_row, page_row = Adw.ComboRow(title="Site", model=Gtk.StringList.new(tuple(sites))), Adw.SpinRow.new_with_range(1, 1000, 1)
site_row.get_template_child(Adw.ComboRow, "popover").connect("closed", lambda *_: search_popover.popdown())
site_row.connect("notify::selected", lambda *_: search_popover.popdown())
page_row.props.title = "Page"
for i in (site_row, page_row): search_popover.props.child.append(i)
search_box = Gtk.Box(css_name="search")
search_box.append(Button(t="menu", icon_name="view-more", tooltip_text="More", popover=search_popover))
search = Gtk.Text(placeholder_text="Search", hexpand=True)
search_list = Gtk.ListBox()
def select_suggestion(l, r):
    if not r: return
    app.modifying = True
    nt, p = search_current_word(r.props.child.i["value"])
    search.props.text = nt
    search.set_position(p)
    app.modifying = False
search_list.connect("row-selected", select_suggestion)
search_list.connect("row-activated", lambda l, r: (select_suggestion(l, r), do_search()))
suggestions_popover = Gtk.Popover(child=Gtk.ScrolledWindow(child=search_list, hexpand=True, max_content_width=365, propagate_natural_height=True, propagate_natural_width=True, valign=1, vscrollbar_policy=3, width_request=300), autohide=False, can_focus=False, halign=3, has_arrow=False, hexpand=True, valign=1)
suggestions_popover.set_parent(search)
def search_current_word(v=None):
    q = search.props.text.split(" ")
    length, closest_index = 0, -1
    for i, word in enumerate(i for i in q):
        length += len(word) + 1
        if length > search.props.cursor_position:
            closest_index = i
            if i > 0 and (search.props.cursor_position - (length - len(word) - 1)) < (length - search.props.cursor_position):
                closest_index = i - 1
            break
    if v:
        pw = q[closest_index]
        q[closest_index] = v
        return (" ".join(q), length - len(pw) + len(v) - 1)
    return q[closest_index]
def search_suggestions(m, b):
    response = m.send_and_read_finish(b)
    if not response:
        app.modiying = False
        return
    GLib.idle_add(search_list.remove_all)
    for i in json.loads(response.get_data().decode("utf-8")):
        box = Gtk.Box()
        box.append(Gtk.Label(label=f"{i['antecedent']} → {i['label']}" if "antecedent" in i else i["label"]))
        if "post_count" in i: box.append(Gtk.Label(css_classes=("dimmed",), label=f"({i['post_count']})"))
        box.i = i
        GLib.idle_add(search_list.append, box)
    app.modifying = False
    GLib.idle_add(suggestions_popover.popup)
    if not search_list.get_first_child(): GLib.idle_add(suggestions_popover.popdown)
def search_changed(*_):
    if app.modifying or not search.props.text: return
    app.modifying = True
    m = Soup.Message.new("GET", f"{sites['Danbooru']['url']}/autocomplete.json?search[query]={search_current_word()}&search[type]=tag_query&limit=15")
    response = session.send_and_read_async(m, GLib.PRIORITY_DEFAULT, None, search_suggestions)
search.connect("notify::text", search_changed)
search_event = Gtk.EventControllerKey()
def search_input(e, kv, kc, s):
    if kc == 9:
        suggestions_popover.popdown()
        return True
    if suggestions_popover.get_mapped():
        selected = search_list.get_selected_row()
        if kc == 111 or kc == 116:
            new = (selected.get_prev_sibling() if kc == 111 and selected else selected.get_next_sibling() if kc == 116 and selected else search_list.get_first_child())
            if new == None:
                new = search_list.get_first_child() if kc == 116 else search_list.get_last_child()
            search_list.select_row(new)
            return True
search_event.connect("key-pressed", search_input)
search.add_controller(search_event)
search_box.append(search)
def do_search(*_):
    suggestions_popover.popdown()
    if hasattr(view.props.selected_page.props.child.props.child, "q"): del view.props.selected_page.props.child.props.child.q
    Gio.Task().run_in_thread(lambda *_: tab_load(q=[search.props.text, int(page_row.props.value), site_row.props.selected_item.get_string(), ()]))
search.connect("activate", do_search)
search_box.append(Button(icon_name="edit-find", tooltip_text="Search", callback=do_search))
view = Adw.TabView(focusable=True)
click = Gtk.GestureClick()
click.connect("released", lambda *_: view.grab_focus())
view.add_controller(click)
def tab_history(b):
    view.props.selected_page.index += (1 if "next" in b.props.icon_name else -1)
    view.props.selected_page.history[view.props.selected_page.index][3] = []
    Gio.Task().run_in_thread(lambda *_: tab_load())
multi = Adw.MultiLayoutView()
for i, w in (("view", view), ("search", search_box),
            ("previous", Button(icon_name="go-previous", tooltip_text="Back", callback=tab_history)),
            ("next", Button(icon_name="go-next", tooltip_text="Forward", callback=tab_history)),
            ("menu", Button(t="menu", menu_model=menus[3], tooltip_text="Menu", icon_name="open-menu"))):
    multi.set_child(i, w)
wide, wide_header = Adw.ToolbarView(content=Adw.LayoutSlot.new("view")), Adw.HeaderBar(title_widget=Adw.Clamp(hexpand=True, child=Adw.LayoutSlot.new("search"), maximum_size=400))
for i in (wide_header, Adw.TabBar(view=view)): wide.add_top_bar(i)
narrow, narrow_header = Adw.ToolbarView(content=Adw.LayoutSlot.new("view")), Adw.HeaderBar(show_title=False, show_end_title_buttons=False)
for i in (Adw.LayoutSlot.new("search"), narrow_header): narrow.add_bottom_bar(i)
wide.bind_property("reveal-top-bars", narrow, "reveal-bottom-bars", 0)
Action("fullscreen", ("F11",), lambda *_: wide.set_reveal_top_bars(not wide.props.reveal_top_bars))
for i, n in ((wide, "wide"), (narrow, "narrow")): multi.add_layout(Adw.Layout(content=i, name=n))
for i in ("previous", "next"): (wide_header.pack_start(Adw.LayoutSlot.new(i)), narrow_header.pack_start(Adw.LayoutSlot.new(i)))
for i in ("menu",): (wide_header.pack_end(Adw.LayoutSlot.new(i)), narrow_header.pack_end(Adw.LayoutSlot.new(i)))
wide_header.pack_start(Button(icon_name="tab-new", tooltip_text="New Tab", action_name="app.new-tab"))
narrow_header.pack_start(Adw.TabButton(view=view, action_name="app.overview"))
overview = Adw.TabOverview(child=multi, enable_new_tab=True, view=view, secondary_menu=menus[3])
Action("overview", ("<primary><shift>o",), lambda *_: overview.set_open(not overview.props.open))
toast_overlay = Adw.ToastOverlay(child=overview)
controller_key, overview_drop = Gtk.EventControllerKey(), Gtk.DropTarget(preload=True, actions=1, formats=Gdk.ContentFormats.parse("GdkTexture GdkFileList GFile"))
def key_pressed(e, kv, kc, s):
    if hasattr(view.props.selected_page, "viewport"):
        if kv in (119, 65362) or kv in (115, 65364):
            adj = view.props.selected_page.viewport.get_vadjustment()
            adj.props.value += adj.props.step_increment if kv == 115 or kv == 65364 else -adj.props.step_increment
            return True
        elif kv in (97, 65361) or kv in (100, 65363):
            adj = view.props.selected_page.viewport.get_hadjustment()
            adj.props.value += adj.props.step_increment if kv == 100 or kv == 65363 else -adj.props.step_increment
            return True
    if kv == 65307: suggestions_popover.popdown()
    if kv == 32:
        t = view.props.selected_page.props.child.props.child
        if hasattr(t, "post") and isinstance(t.post.props.child, Gtk.Video):
            if t.post.props.child.props.media_stream.props.playing: t.post.props.child.props.media_stream.pause()
            else: t.post.props.child.props.media_stream.play()
            return True
    if kv == 118 and s == 4:
        c = app.props.active_window.props.display.get_clipboard()
        if c.props.formats.contain_gtype(Gdk.Texture):
            c.read_texture_async(None, lambda cl, r: add(cl.read_texture_finish(r)))
            return True
        elif c.props.formats.contain_gtype(Gdk.FileList):
            c.read_value_async(Gdk.FileList, 0, None, lambda cl, r: add(cl.read_value_finish(r)))
            return True
controller_key.connect("key-pressed", key_pressed)
overview_drop.connect("drop", lambda d, v, *_: add(v))
for i in (controller_key, overview_drop): toast_overlay.add_controller(i)
file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))
_breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(1, 700, 0))
_breakpoint.add_setter(multi, "layout-name", "narrow")

def tag_clicked(e, *_):
    q = view.props.selected_page.history[view.props.selected_page.index]
    match e.props.button:
        case 1: Gio.Task().run_in_thread(lambda *_: tab_load(q=[e.props.widget.props.label, 1, q[2], ()]))
        case 2: Tab(q=e.props.widget.props.label, s=q[2])
        case 3:
            if e.props.widget.get_ancestor(TagRow) != prefs["Blacklist"]:
                t = f"{e.props.widget.props.label} "
                if e.props.widget.props.label in prefs["Blacklist"].tags:
                    t += "removed from "
                    prefs["Blacklist"].tags = [i for i in prefs["Blacklist"].tags if not i == e.props.widget.props.label]
                else:
                    t += "added to "
                    prefs["Blacklist"].tags = prefs["Blacklist"].tags + [e.props.widget.props.label]
            (edit if edit.get_mapped() else toast_overlay).add_toast(Adw.Toast(timeout=2, title=t + "blacklist"))
def tag_widget_added(r, tag):
    for n in range(3):
        e = Gtk.GestureClick(button=n + 1)
        e.connect("pressed", tag_clicked)
        tag.get_first_child().add_controller(e)
def set_colors(pt=False, p=False):
    if pt and p:
        if hasattr(pt, "con"): pt.disconnect(pt.con)
        p.colors = palette(pt, distance=128, black_white=64)
    p = view.props.selected_page.props.child.props.child.post if hasattr(view.props.selected_page.props.child.props.child, "post") else None
    if app.props.active_window and hasattr(p, "colors") and prefs["View > Post Colors Theming"].props.active:
        style = Gtk.CssProvider()
        GLib.idle_add(style.load_from_string, ":root {" + "".join(tuple(f"--color-{i + 1}: rgb{color};" for i, color in enumerate(p.colors))) + "}")
        GLib.idle_add(Gtk.StyleContext.add_provider_for_display, *(app.props.active_window.props.display, style, 700))
        GLib.idle_add(app.props.active_window.add_css_class, "colored")
    elif app.props.active_window: GLib.idle_add(app.props.active_window.remove_css_class, "colored")
def deprecated_web_animate(p, *_): # REMOVE WHEN GTK.MEDIAFILE INPUT STREAM IS SUPPORTED
    if p.get_mapped(): (f := p.image.next_frame(), p.set_paintable(GlyGtk4.frame_get_texture(f)), GLib.timeout_add(f.get_delay() / 1000, deprecated_web_animate, p))
def post_video(p):
    media = Gtk.Video(file=p.child, loop=True, valign=0 if p.p else 3)
    media.bind_property("loop", media.props.media_stream,  "loop", 0 | 2)
    media.get_template_child(Gtk.Video, "graphics_offload").props.black_background = False
    if p.p:
        media.get_template_child(Gtk.Video, "controls_revealer").props.visible = media.get_template_child(Gtk.Video, "overlay_icon").props.visible = False
    else:
        pt = media.get_template_child(Gtk.Video, "video_picture").props.paintable
        pt.con = pt.connect("invalidate-contents", lambda ptb, po: Gio.Task().run_in_thread(lambda *_: set_colors(ptb, po)), p)
    GLib.idle_add(p.set_child, media)
def load_picture(a, r, p):
    try:
        if isinstance(a, Soup.Session): return Gly.Loader.new_for_bytes(a.send_and_read_finish(r)).load_async(None, load_picture, p)
        image = a.load_finish(r)
        frame = image.next_frame()
        if frame.get_delay() > 0 and not p.child.get_uri().startswith("http") and not p.p:
            return post_video(p)
        texture = GlyGtk4.frame_get_texture(frame)
        if not p.p: Gio.Task().run_in_thread(lambda *_: set_colors(texture, p))
        pic = Gtk.Picture(valign=0 if p else 3, content_fit=1 if p else 3, paintable=texture)
        if frame.get_delay() > 0 and not p.p:
            pic.image = image
            pic.connect("map", deprecated_web_animate)
        GLib.idle_add(p.set_child, pic)
    except Exception as e: GLib.idle_add(p.set_child, Adw.StatusPage(icon_name="folder-pictures-symbolic", tooltip_text=e))
def show_revealer(e, *_):
    p = e.post
    if os.path.exists(p.preview_file.peek_path()) and os.path.exists(p.file.peek_path()):
        p.download.props.tooltip_text, p.download.props.icon_name = "Open", "folder-open-symbolic"
    else:
        p.download.props.tooltip_text, p.download.props.icon_name = "Download", "folder-download-symbolic"
    if tuple(i for i in app.data[0][p.s] if i["id"] == p.o["id"]):
        p.favorite.props.icon_name, p.favorite.props.tooltip_text = "starred-symbolic", "Remove Favorite"
    else:
        p.favorite.props.icon_name, p.favorite.props.tooltip_text = "star-new-symbolic", "Add Favorite"
    p_id = get_property(p.o, "parent_id", p.s)
    has_c = get_property(p.o, "has_children", p.s)
    tt = "Has Parent" if p_id else "Has Children"
    i = "folder-user" if p_id else "preferences-system-parental-controls"
    if p_id and has_c:
        tt, i = "Has Parent and Children", "system-users"
    p.related.props.tooltip_text, p.related.props.icon_name, p.related.props.visible = tt, i + "-symbolic", int(p_id) > 0 or has_c
    p.revealer.props.reveal_child = True
def post_finish_download(a, r, d):
    b = a.send_and_read_finish(r)
    if b: d[1].replace_contents_bytes_async(b, None, False, 0)
    if d[0].props.root:
        t = view.get_page(d[0].get_ancestor(MasonryBox).get_ancestor(Adw.Bin)) if d[0].get_ancestor(MasonryBox) else view.get_page(d[0].get_ancestor(Gtk.Overlay).get_ancestor(Adw.Bin))
        GLib.idle_add(t.set_loading, False)
        show_revealer(d[0].event)
def post_download(b, download=False):
    p = download if download else b.get_ancestor(Gtk.Overlay).post if hasattr(b.get_ancestor(Gtk.Overlay), "post") else b.get_ancestor(Gtk.Overlay)
    if os.path.exists(p.file.peek_path()) and os.path.exists(p.preview_file.peek_path()):
        None if download else (file_launcher.set_file(p.preview_file if p.p else p.file), file_launcher.open_containing_folder())
    else:
        view.props.selected_page.props.loading = True
        for f, u in ((p.preview_file, get_property(p.o, "preview_url", p.s)), (p.file, get_property(p.o, "file_url", p.s))): session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, post_finish_download, (p, f))
Action("download", ("<primary>s",), lambda *_: view.props.selected_page.props.child.props.child.post.download.emit("clicked") if hasattr(view.props.selected_page.props.child.props.child, "post") else None)
def post_related(b):
    p = b.get_ancestor(Gtk.Overlay).post if hasattr(b.get_ancestor(Gtk.Overlay), "post") else b.get_ancestor(Gtk.Overlay)
    p_id = get_property(p.o, "parent_id", p.s)
    has_c = get_property(p.o, "has_children", p.s)
    if p_id: Tab(q=f"parent:{p_id}", s=p.s)
    if has_c: Tab(q=f"parent:{p.o['id']}", s=p.s)
def post_favorite(b):
    p = b.get_ancestor(Gtk.Overlay).post if hasattr(b.get_ancestor(Gtk.Overlay), "post") else b.get_ancestor(Gtk.Overlay)
    if tuple(i for i in app.data[0][p.s] if i["id"] == p.o["id"]):
        app.data[0][p.s] = [i for i in app.data[0][p.s] if i["id"] != p.o["id"]]
    else:
        p.o["added"] = GLib.DateTime.new_now_utc().to_unix()
        app.data[0][p.s].append(p.o)
        if prefs["Favorites > Download Favorites"].props.active: post_download(p.download, p)
    show_revealer(p.event)
def Post(o, s, p=False):
    widget = Gtk.Overlay(halign=0) if p else Adw.Bin(halign=3)
    widget.p, widget.o, widget.s = p, o, s
    buttons = (Button(name="download", callback=post_download), Button(name="favorite", callback=post_favorite), Button(name="edit", icon_name="view-more", tooltip_text="More", callback=show_edit), Button(name="related", callback=post_related))
    for i in buttons: setattr(widget, i.props.name, i)
    widget.revealer = Gtk.Revealer(child=Gtk.Box(), valign=1, transition_type=1)
    widget.event = Gtk.EventControllerMotion()
    widget.event.post = widget
    widget.event.connect("enter", show_revealer)
    widget.event.bind_property("contains-pointer", widget.revealer, "reveal-child", 0 | 2)
    _hash = get_property(o, "hash", s)
    widget.child = get_property(o, "file_url", s)
    widget.file, widget.preview_file = tuple(app_data.get_child(i) for i in (f"{_hash}.{widget.child.rsplit('.')[-1]}", f"preview-{_hash}.{get_property(o, 'preview_url', s).rsplit('.')[-1]}"))
    if not widget.child or p:
        widget.child = get_property(o, "preview_url", s)
    if get_property(o, "file_url", s) and os.path.exists(widget.file.peek_path()):
        widget.child = widget.file
    if get_property(o, "preview_url", s) and os.path.exists(widget.preview_file.peek_path()) and (not widget.child or p):
        widget.child = widget.preview_file
    if widget.child:
        widget.child = Gio.File.new_for_uri(widget.child) if isinstance(widget.child, str) else widget.child
        if widget.child.peek_path() and not os.path.exists(widget.child.peek_path()):
            if prefs["Favorites > Download Favorites"].props.active and o in app.data[0][s]: post_download(widget.download, widget)
        if Gio.content_type_guess(widget.child.get_uri())[0].startswith("video"): GLib.idle_add(post_video, widget)
        else:
            widget.props.child = Adw.Spinner()
            if widget.child.get_uri().startswith("http"): session.send_and_read_async(Soup.Message.new("GET", widget.child.get_uri()), GLib.PRIORITY_DEFAULT, None, load_picture, widget)
            else: Gly.Loader.new(widget.child).load_async(None, load_picture, widget)
    else:
        widget.props.child = Adw.StatusPage(icon_name="folder-pictures-symbolic", title="Resource Not Available")
    return widget

def catalog_activate(m, c, b):
    match b:
        case 1: tab_load(q=[c.o, 1, c.s, []])
        case 2: Tab(q=c.o, s=c.s)
        case 3: c.favorite.emit("clicked")
def catalog_load_more(sw, p):
    content = sw.props.parent
    if p == 3 and not content.count[0] >= content.count[1]:
        t = view.get_page(content.get_ancestor(Adw.Bin))
        if not t.props.loading: Gio.Task().run_in_thread(lambda *_: tab_load(t=t, page=True))
def tab_changed(*_):
    GLib.idle_add(set_colors)
    v = view.props.selected_page
    if not hasattr(v, "history"): return
    multi.get_child("previous").props.sensitive = len(v.history) - 1 >= v.index and v.index != 0 
    multi.get_child("next").props.sensitive = len(v.history) > v.index + 1 
    q = v.history[v.index]
    site_row.props.selected = tuple(sites).index(q[2])
    page_row.props.value = q[1]
    if not isinstance(q[0], list):
        app.modifying = True
        search.set_text(f"id:{q[0]['id']}" if isinstance(q[0], dict) else q[0])
        app.modifying = False
        search.set_position(-1)
    content = v.props.child.props.child
    if v.props.loading or isinstance(content, Adw.Spinner) or hasattr(content, "q") and content.q == q: return
    Gio.Task().run_in_thread(lambda *_: tab_load())
view.connect("notify::selected-page", tab_changed)
app.closed = []
Action("reopen-tab", ("<primary><shift>t",), lambda *_: (q := app.closed.pop(-1), Tab(q=q[0], p=q[1], s=q[2])) if app.closed else None)
def tab_operation(a, b=False, t=False):
    if not t:
        t = view.t if "context" in a.props.name and isinstance(a, Gio.SimpleAction) else b if isinstance(b, Adw.TabPage) else view.props.selected_page
    if (isinstance(a, Adw.TabView) or (isinstance(a, Gio.SimpleAction) and "close" in a.props.name)):
        if t.props.pinned: return
        else:
            view.close_page(t) if isinstance(a, Gio.SimpleAction) else None
            app.closed.append(t.history[t.index])
            if hasattr(t.props.child.props.child, "post") and isinstance(t.props.child.props.child.post.props.child, Gtk.Video):
                t.props.child.props.child.post.props.child.props.media_stream.props.playing = False
        return
    q = t.history[t.index]
    if "open-current" in a.props.name:
        uri = sites[q[2]]["get_url"](q)
        if isinstance(uri, Gio.File):
            file_launcher.props.file = uri
            file_launcher.launch()
        else:
            uri_launcher.props.uri = uri
            uri_launcher.launch()
        return
    if isinstance(q[0], dict) and not hasattr(t.props.child.props.child, "post"):
        tab_load(t)
        return GLib.idle_add(lambda *_: tab_operation(a, t=t))
    if hasattr(t.props.child.props.child, "post"):
        if "constrain" in a.props.name: t.viewport.set_vscroll_policy(not t.viewport.props.vscroll_policy)
        if "favorite" in a.props.name: t.props.child.props.child.post.favorite.emit("clicked")
        if "edit" in a.props.name: t.props.child.props.child.post.edit.emit("clicked")
    else:
        if "favorite" in a.props.name:
            q = q[0]
            prefs["Bookmarks"].tags = [i for i in prefs["Bookmarks"].tags if not i == q] if q in prefs["Bookmarks"].tags else [i for i in prefs["Bookmarks"].tags] + [q]
            toast_overlay.add_toast(Adw.Toast(title=f"{q} {'added to' if q in prefs['Bookmarks'].tags else 'removed from'} bookmarks", timeout=3))
view.connect("close-page", tab_operation)
for n, k in (("edit", "e"), ("favorite", "d"), ("close", "w"), ("open-current", "o"), ("toggle-constrain", "f")): (Action(n, (f"<primary>{k}",), tab_operation), Action("context-" + n, (), tab_operation))
Action("context-pin", [], lambda *_: view.set_page_pinned(view.t, not view.t.props.pinned))
def tab_setup_menu(v, t):
    v.t = t
    if not v.t: return
    q = v.t.history[v.t.index]
    v.props.menu_model.remove_all()
    tab_menu, tab_context_menu = Gio.Menu.new(), Gio.Menu.new()
    tab_context_menu.append("Open in Browser", "app.context-open-current")
    if isinstance(q[0], dict): tab_context_menu.append("Edit", "app.context-edit")
    tab_context_menu.append(("Remove Favorite" if tuple(i for i in app.data[0][q[2]] if i["id"] == q[0]["id"]) else "Add Favorite") if isinstance(q[0], dict) else ("Remove Bookmark" if q[0] in prefs["Bookmarks"].tags else "Add Bookmark"), "app.context-favorite")
    tab_menu.append("Unpin Tab" if v.t.props.pinned else "Pin Tab", "app.context-pin")
    tab_menu.append("Close Tab", "app.context-close")
    for i in (tab_context_menu, tab_menu): v.props.menu_model.append_section(None, i)
view.set_menu_model(Gio.Menu.new())
view.connect("setup-menu", tab_setup_menu)
def catalog_add_post(catalog, o, s):
    post = Post(o, s, True)
    h, w = get_property(o, "height", s), get_property(o, "width", s)
    post.height = max(h, 1) / max(w, 1)
    for b in (post.download, post.favorite, post.edit, post.related):
        (b.add_css_class("osd"), b.add_css_class("circular"))
    for i in (post.download, post.favorite): (post.revealer.props.child.append(i), i.set_valign(1))
    post.favorite.props.hexpand, post.favorite.props.halign = True, 2
    post.revealer.props.child.append(Gtk.Box(orientation=1))
    for i in (post.edit, post.related): post.revealer.props.child.get_last_child().append(i)
    GLib.idle_add(post.add_overlay, post.revealer)
    GLib.idle_add(post.add_controller, post.event)
    duration = get_property(o, "duration", s)
    if duration: GLib.idle_add(post.add_overlay, Gtk.Label(css_classes=("osd",), valign=2, halign=1, label=duration[3:] if duration.startswith("00:") else duration))
    GLib.idle_add(catalog.add, post)
def tab_load(t=None, page=False, q=[]):
    GLib.idle_add(suggestions_popover.popdown)
    t = t if t else view.props.selected_page
    content = t.props.child.props.child
    if q:
        t.index = len(t.history)
        t.history.append(q)
    q = t.history[t.index]
    if content and not page and hasattr(content, "q") and content.q == q: return
    if page and not (q[3] and q[2] != "Favorites"):
        q[1] += 1
    if t == view.props.selected_page:
        multi.get_child("previous").props.sensitive = len(t.history) - 1 >= t.index and t.index != 0 
        multi.get_child("next").props.sensitive = len(t.history) > t.index + 1
    app.props.active_window.remove_css_class("colored") if app.props.active_window else None
    if q[3]:
        catalog = q[3][:limit]
    else:
        if isinstance(q[0], str):
            if not page: GLib.idle_add(t.props.child.set_child, Adw.Spinner())
            GLib.idle_add(t.set_loading, True)
            if q[2] == "Favorites":
                q[3] = fetch_favorite_catalog(q[0])
                count, q[3] = len(q[3]), q[3][limit * q[1]:] if q[1] > 1 else q[3]
            else:
                try:
                    count, q[3] = fetch_online_catalog(q[2], q[0], q[1], not page)
                except Exception as e:
                    print(e)
                    GLib.timeout_add(200, t.set_loading, False)
                    return GLib.idle_add(t.props.child.set_child, Adw.StatusPage(description=f"{e}", icon_name="dialog-error-symbolic", title="Error!"))
            catalog = q[3][:limit]
            if not page: GLib.idle_add(t.set_title, f"{q[0]} ({count}) ({q[2]})")
        elif isinstance(q[0], dict):
            catalog = (q[0],)
    q[3] = tuple(i for i in q[3] if not i in catalog)
    if not catalog and not page:
        content = Adw.StatusPage(description=f"No posts for page {q[1]}\nTry a different search", icon_name="edit-find-symbolic", title="No Results")
    elif len(catalog) == 1 and not page:
        t.viewport = Gtk.Viewport(vscroll_policy = int(not prefs["View > Constrain Post Size"].props.active))
        t.viewport.bind_property("vscroll-policy", t.viewport, "hscroll-policy", 0 | 2)
        content = Gtk.Overlay(child=Gtk.ScrolledWindow(child=t.viewport, propagate_natural_height=True, propagate_natural_width=True))
        t.viewport.props.child = content.post = Post(catalog[0][0] if isinstance(catalog[0], tuple) else catalog[0], catalog[0][1] if isinstance(catalog[0], tuple) else q[2])
        content.post.revealer.props.child.add_css_class("linked")
        content.post.revealer.props.child.props.halign = 2
        for i in ("download", "favorite", "related", "edit"): content.post.revealer.props.child.append(getattr(content.post, i))
        content.add_overlay(content.post.revealer)
        content.add_controller(content.post.event)
        GLib.idle_add(t.set_title, f"post {content.post.o['id']} ({content.post.s})")
    else:
        if page:
            content.count[0] += len(catalog)
        else:
            content = MasonryBox(activate=catalog_activate)
            t.viewport = content.props.child
            content.count = [len(catalog), count]
            content.props.child.connect("edge-reached", catalog_load_more)
        for i in catalog:
            if any(it in get_property(i, "tags", i[1]) for it in prefs["Blacklist"].tags): continue
            catalog_add_post(content, i[0] if q[2] == "Favorites" else i, i[1] if q[2] == "Favorites" else q[2])
        total_pages = -(-content.count[1] // limit)
        GLib.idle_add(toast_overlay.add_toast, Adw.Toast(timeout=2, title=f"Page {q[1]} of {total_pages}"))
    content.q = q
    GLib.idle_add(t.props.child.set_child, content)
    GLib.timeout_add(200, t.set_loading, False)
    GLib.timeout_add(200, suggestions_popover.popdown)
    if t.props.child.get_mapped():
        site_row.props.selected = tuple(sites).index(q[2])
        page_row.props.value = q[1]
def Tab(*_, q=None, p=1, s=""):
    tab = view.add_page(Adw.Bin())
    q, s = prefs["Tabs > New Tab Query"].props.text if q == None else q, s if s else prefs["Tabs > New Tab Site"].props.selected_item.get_string()
    tab.props.title, tab.history, tab.index = f"post {q['id']} ({s})" if isinstance(q, dict) else f"{q} ({s})", [[q, p, s, ()]], 0
    return tab
Action("new-tab", ["<primary>t"], Tab)
overview.connect("create-tab", Tab)

def sync_post(*_):
    if app.modifying: return
    p = edit.p
    for l in (editable, dates):
        for i in l:
            w, prop = i if isinstance(i, Gtk.Calendar) else i[0], "date" if isinstance(i, Gtk.Calendar) else i[1]
            if not w.get_ancestor(Adw.PreferencesRow).get_mapped(): continue
            v = getattr(w.props, prop)
            names = w.props.name.split(" || ")
            for name in names:
                if name in sites[p.s]["overrides"] and callable(sites[p.s]["overrides"][name][1]):
                    v = sites[p.s]["overrides"][name][1](v)
            for name in names:
                if name in p.o:
                    p.o[name] = v.to_utc().to_unix() if isinstance(v, GLib.DateTime) else v
    app.data[0][p.s] = [p.o if i["id"] == p.o["id"] else i for i in app.data[0][p.s]]
def show_edit(b, *_):
    app.modifying = True
    edit.p = p = b.get_ancestor(Gtk.Overlay).post if hasattr(b.get_ancestor(Gtk.Overlay), "post") else b.get_ancestor(Gtk.Overlay)
    for i in info:
        if i.props.title == "Format":
            i.props.subtitle = Gio.content_type_get_description(Gio.content_type_guess(get_property(p.o, "file_url", p.s))[0])
        else:
            v = get_property(p.o, i.props.title.lower(), p.s)
            i.props.visible = bool(v)
            if v:
                i.props.subtitle = str(v)
    for i in dates:
        v = get_property(p.o, i.props.name, p.s)
        i.get_ancestor(Adw.PreferencesRow).props.visible = bool(v)
        if i.get_ancestor(Adw.PreferencesRow).props.visible:
            i.props.date = GLib.DateTime.new_from_unix_utc(v) if isinstance(v, int) else v
    for i in editable:
        v = get_property(p.o, i[0].props.name, p.s)
        i[0].props.visible = v != None
        if v != None: setattr(i[0].props, i[1], v)
    edit.present(app.props.active_window)
    app.data[0][p.s] = [p.o if i["id"] == p.o["id"] else i for i in app.data[0][p.s]]
    app.modifying = False
edit = Adw.PreferencesDialog(content_height=530, content_width=530, search_enabled=True)
pages = (Adw.PreferencesPage(icon_name="tag-outline-symbolic", title="Tags"), Adw.PreferencesPage(icon_name="document-edit-symbolic", title="Edit"), Adw.PreferencesPage(icon_name="help-about-symbolic", title="Info"))
for i in pages: edit.add(i)
dates = [Gtk.Calendar(name=i) for i in ("added", "created_at", "updated_at || changed")]
for i in dates: Button(t="menu", css_classes=["flat"], icon_name="month", popover=Gtk.Popover(child=i), valign=3, tooltip_text="Pick a Date")
editable = ((TagRow(name="tags || tag_string", title="Tags"), "tags"),
            (Adw.EntryRow(title="Source", name="source"), "text"),
            (Adw.EntryRow(title="File URL", name="file_url"), "text"),
            (Adw.EntryRow(title="Preview URL", name="preview_url || preview_file_url"), "text"),
            (Adw.SpinRow(title="Parent ID", name="parent_id", adjustment=Gtk.Adjustment.new(0, 0, 1e8, 1, 10, 10)), "value"),
            (Adw.SwitchRow(title="Has Children", name="has_children"), "active"),
            (Adw.ToggleGroup(name="rating", valign=3), "active"))
editable[0][0].connect("tag-widget-added", tag_widget_added)
for i in ratings: editable[-1][0].add(Adw.Toggle(label=i[:1], tooltip=i))
for i in dates: i.connect(f"notify::date", sync_post)
for i in editable: i[0].connect(f"notify::{i[1]}", sync_post)

group = Adw.PreferencesGroup(separate_rows=True)
ai_tag_button = Adw.ButtonRow(title="AI Autotag", css_classes=["button", "activatable", "suggested-action"], tooltip_text="Upload to Danbooru AI Tagger")
def ai_ai(b):
    paintable = edit.p.props.child.props.paintable if isinstance(edit.p.props.child, Gtk.Picture) else edit.p.props.child.props.media_stream
    form_data = Soup.Multipart.new("multipart/form-data")
    form_data.append_form_file("file", "image.png", "image/png", paintable.get_current_image().save_to_png_bytes())
    form_data.append_form_string("format", "json")
    mes = Soup.Message.new_from_multipart("https://autotagger.donmai.us/evaluate", form_data)   
    b = session.send_and_read(mes)
    if mes.get_status() == 200:
        editable[0][0].tags = [i for i in json.loads(b.get_data())[0]["tags"]]
        edit.add_toast(Adw.Toast(title=f"Done!", timeout=2))
    else:
        edit.add_toast(Adw.Toast(title=f"Server returned {mes.get_status()}!"))
ai_tag_button.connect("activated", ai_ai)
group.add(ai_tag_button)
group.add(editable[0][0])
pages[0].add(group)

info = tuple(Adw.ActionRow(title=i, subtitle_selectable=True, css_classes=("property",)) for i in ("ID", "Uploader", "Size", "Format", "Hash"))
for n, i in ((1, tuple(i[0] for i in editable[1:])), (1, dates), (2, info)):
    group = Adw.PreferencesGroup()
    for it in i:
        if isinstance(it, Gtk.Calendar):
            r = Adw.ActionRow(title=it.props.name.title().split(" || ")[0].replace("_", " "))
            it.bind_property("date", r, "subtitle", 0 | 2, lambda b, v: v.to_local().format("%x %T"))
            r.add_suffix(Button(t="menu", css_classes=("flat",), icon_name="month", popover=Gtk.Popover(child=it), valign=3, tooltip_text="Pick a Date"))
            group.add(r)
        elif isinstance(it, Adw.PreferencesRow):
            group.add(it)
        elif isinstance(it, Adw.ToggleGroup):
            (r := Adw.ActionRow(title=it.props.name.title()), r.add_suffix(it), group.add(r))
    pages[n].add(group)

data_file = app_data.get_child(about.props.application_name)
if not os.path.exists(app_data.peek_path()): app_data.make_directory()
app.data = marshal.loads(data_file.load_contents()[1]) if os.path.exists(data_file.peek_path()) else ({}, {})
for i in sites: app.data[0].setdefault(i, [])
for i, v in (("General", {"Tabs": {"New Tab Site": "Danbooru", "New Tab Query": "", "Restore Tabs": True},
        "Favorites": {"Delete Unused": False, "Download Favorites": False},
        "View": {"Safe Mode": True, "Autocomplete": False, "Constrain Post Size": True, "Post Colors Theming": True}}), ("Tags", {"Bookmarks": [],"Blacklist": []}), ("Accounts", {"Danbooru": {"User": "", "Token": ""}, "Gelbooru": {"User": "", "Token": ""}}), ("Restore", ()), ("Window", {"default-width": 600, "default-height": 600, "maximized": False})): app.data[1].setdefault(i, v)
preferences, prefs = Adw.PreferencesDialog(search_enabled=True, content_width=530, content_height=600), {}
Action("preferences", ("<primary>p",), lambda *_: preferences.present(app.props.active_window))
pages = tuple(Adw.PreferencesPage(title=i) for i in tuple(app.data[1])[:3])
for n, i in enumerate(("preferences-system", "tag-outline", "folder-user")): pages[n].set_icon_name(f"{i}-symbolic")
for p in pages:
    for g in app.data[1][p.props.title]:
        g = Adw.PreferencesGroup(title=g)
        if p.props.title == "Tags":
            r = TagRow(name=g.props.title)
            r.connect("tag-widget-added", tag_widget_added)
            r.tags = app.data[1][p.props.title][g.props.title]
            prefs[f"{g.props.title}"] = r
            g.add(r)
        else:
            for n, v in app.data[1][p.props.title][g.props.title].items():
                if type(v) == bool:
                    r = Adw.SwitchRow(active=v)
                elif n in ("New Tab Site"):
                    r = Adw.ComboRow(model=Gtk.StringList.new(tuple(sites)))
                    r.props.selected = r.props.model.find(v)
                else:
                    r = Adw.EntryRow(text=v)
                r.props.title = n
                prefs[f"{g.props.title} > {n}"] = r
                g.add(r)
        p.add(g)
    preferences.add(p)
if prefs["Favorites > Delete Unused"].props.active:
    for i in os.listdir(app_data.get_path()):
        if i in (about.props.application_name, about.props.application_name + "~"): continue
        u = False
        for s,v in app.data[0].items():
            for p in v:
                _hash = get_property(o, "hash", s)
                if i in (f"{_hash}.{get_property(p, 'file_url', s).rsplit('.')[-1]}", f"preview-{_hash}.{get_property(p, 'preview_url', s).rsplit('.')[-1]}"):
                    u = True
        if not u: app_data.get_child(i).delete()
if prefs["Tabs > Restore Tabs"].props.active:
    for i in app.data[1]["Restore"]:
        t = Tab(q=i[0], p=i[1], s=i[2])
        view.set_page_pinned(t, i[3])
if not view.props.selected_page: Tab()
tab_changed()
app.connect("activate", lambda a: (w := Adw.ApplicationWindow(application=a, content=toast_overlay, title=about.props.application_name, default_width=app.data[1]["Window"]["default-width"], default_height=app.data[1]["Window"]["default-height"], maximized=app.data[1]["Window"]["maximized"]), w.add_breakpoint(_breakpoint), w.present(), GLib.timeout_add(400, set_colors))[3] if not a.props.active_window else None)
app.connect("window-removed", lambda a, w: tuple(app.data[1]["Window"].update({i: getattr(w.props, i)}) for i in app.data[1]["Window"]))
def shutdown(*_):
    if prefs["Tabs > Restore Tabs"].props.active:
        app.data[1]["Restore"] = tuple((q[0], q[1], q[2], i.props.pinned) for i in view.props.pages for q in [i.history[i.index]])
    for i in prefs.values():
        if isinstance(i, TagRow):
            app.data[1]["Tags"][i.props.name] = i.props.tags
        else:
            app.data[1][i.get_ancestor(Adw.PreferencesPage).props.title][i.get_ancestor(Adw.PreferencesGroup).props.title][i.props.title] = i.props.active if isinstance(i, Adw.SwitchRow) else i.props.text if isinstance(i, Adw.EntryRow) else i.props.selected_item.get_string() if isinstance(i, Adw.ComboRow) else ""
    data_file.replace_contents(marshal.dumps(app.data), None, True, 0)
app.connect("shutdown", shutdown)
app.run()
