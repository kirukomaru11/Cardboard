#!/usr/bin/python3
from json import loads as json

from AppUtils import *

css = """
tabview :not(masonrybox) .spinner { min-width: 200px; min-height: 400px; }
tabview masonrybox media label { margin: 0px 0px 8px 8px; padding: 6px 10px 6px 10px; border-radius: 14px; font-weight: bold; }
tabview masonrybox media box { border-spacing: 6px; }
media > revealer > box,
widget > media picture { margin: 6px; }
masonrybox button { border-radius: 100px; }
widget > media revealer > box,
masonrybox button,
media > label { background: rgba(0, 0, 0, 0.3); color: white; }
widget > media revealer > box { margin: 6px; border-radius: 9px; }

.bottom-bar search { margin: 4px 6px 2px 6px; min-height: 36px; }
search placeholder { opacity: var(--dim-opacity); }
search {
 background: color-mix(in srgb, currentColor 8%, transparent);
 border-radius: 10px;
 padding: 0px 5px 0px 5px;
 outline: 0 solid transparent;
 outline-offset: 4px;
 transition: outline-color 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94), outline-width 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94), outline-offset 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
search > menubutton > button,
search > button { background: none; outline: none; }
search > menubutton:not(:hover) > button,
search > button:not(:hover) { opacity: 0.7; }
search popover contents > list > row,
search > button,
search > menubutton > button { padding: 0px; }
search:focus-within {
 outline-color: color-mix(in srgb, var(--accent-color) 50%, transparent);
 outline-width: 2px;
 outline-offset: -2px;
}
search > text { margin: 0px 2px 0px 2px; }
search text popover list { background: none; }
search text popover { margin-top: 6px; }
search text popover row:selected { background-color: color-mix(in srgb, currentColor 5%, transparent); }
search text popover row {
  padding: 8px;
  margin-bottom: 2px;
  border-radius: 6px;
}
search text popover row:last-child { margin-bottom: 0px; }
search text popover row box { border-spacing: 4px; }

sheet,
window {
  transition-property: background;
  transition-duration: 250ms;
  transition-timing-function: ease;
}
.colored {
  --scrollbar-outline-color: rgb(0 0 0 / 25%);
  --accent-color: var(--color-1);
  --accent-bg-color: var(--color-1);
  --popover-bg-color: color-mix(in srgb, var(--color-2), var(--window-bg-color) 60%);
  --card-bg-color: rgb(255 255 255 / 4%);
}
.colored sheet,
.colored window {
  background: linear-gradient(
      to bottom right,
      color-mix(in srgb, var(--color-1) 45%, transparent),
      transparent
    ),
    linear-gradient(
      to bottom left,
      color-mix(in srgb, var(--color-2) 45%, transparent),
      transparent
    ),
    linear-gradient(
      to top,
      color-mix(in srgb, var(--color-3) 45%, transparent),
      transparent
    ),
    var(--window-bg-color);
}
.colored controls.toolbar.card,
.colored widget > media revealer > box { background: color-mix(in srgb, var(--color-3), transparent 60%); }
"""

limit, ratings = 30, ("General", "Sensitive", "Questionable", "Explicit")

def shutdown(*_):
    app.data["Tabs"] = tuple((q[0], q[1], q[2], i.get_pinned()) for i in view.get_pages() for q in [i.history[i.index]])
    data_save()
    if getattr(preferences, "Favorites Delete Unused").get_active():
        for i in os.listdir(app.data_folder.peek_path()):
            if i in (app.name, f"{app.name}~"): continue
            u = False
            for s, v in app.data["Favorites"].items():
                for p in v:
                    _hash = get_property(p, "hash", s)
                    if i in (f"{_hash}.{get_property(p, 'file_url', s).rsplit('.')[-1]}", f"preview-{_hash}.{get_property(p, 'preview_url', s).rsplit('.')[-1]}"):
                        u = True
            if not u:
                print("Deleting", i)
                app.data_folder.get_child(i).delete()

app = App(shortcuts={"General": (("Add File", "app.add-file"), ("Add URL", "app.add-url"), ("Paste File/Image/URL", "<primary>v"), ("Keyboard Shortcuts", "app.shortcuts"), ("Preferences", "app.preferences"), ("Fullscreen", "app.fullscreen")), "Tabs": (("Overview", "app.overview"), ("Open in Browser", "app.open-current"), ("New Tab", "app.new-tab"), ("Close Tab", "app.close"), ("Reopen Closed Tab", "app.reopen-tab"), ("Toggle Favorite/Bookmark", "app.favorite"), ("Toggle Constrain", "f"), ("Post More", "app.more"), ("Download Post", "app.download"))},
          shutdown=shutdown,
          application_id="io.github.kirukomaru11.Cardboard",
          style=css,
          data={
            "Window": { "default-height": 600, "default-width": 600, "maximized": False },
            "General": { "Tabs": { "New Tab Site": "Danbooru", "New Tab Query": ""},  "Favorites": { "Delete Unused": False, "Download Favorites": False }, "View": { "Safe Mode": True, "Autocomplete": True, "Constrain Post Size": True, "Post Colors Theming": True }, },
            "Tags": { "Bookmarks": [],"Blacklist": [] },
            "Accounts": {},
            "Tabs": (),
            "Favorites": {}
          })
app.modifying = False
sites = {
    "Favorites": {
        "url": app.data_folder.get_uri(),
        "get_url": lambda q: app.data_folder,
        "overrides": {
            "size": lambda p: f"{p['width']}x{p['height']} ({GLib.format_size(p['size'])})",
            "duration": lambda p: GLib.DateTime.new_from_unix_utc(p["duration"]).format("%T") if p["duration"] > 0 else None,
            "created_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["created_at"]), lambda d: d.to_utc().to_unix()),
            "updated_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["updated_at"]), lambda d: d.to_utc().to_unix()),},},
        "Danbooru": {"url": "https://danbooru.donmai.us",
                     "api": lambda: f"&api_key={getattr(preferences, 'Danbooru Token').get_text()}&login={getattr(preferences, 'Danbooru User').get_text()}" if getattr(preferences, "Danbooru User").get_text() and getattr(preferences, "Danbooru Token").get_text() else ""},
        "Gelbooru": {"url": "https://gelbooru.com",
                     "api": lambda: f"&api_key={getattr(preferences, 'Gelbooru Token').get_text()}&user_id={getattr(preferences, 'Gelbooru User').get_text()}" if getattr(preferences, "Gelbooru User").get_text() and getattr(preferences, "Gelbooru Token").get_text() else ""},
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
        term_sites = tuple(i.split(":")[-1] for i in term_sites if not i.startswith("-") and i.split(":")[-1] in app.data["Favorites"])
        for site in term_sites:
            for p in app.data["Favorites"][site]:
                if not "added" in p:
                    p["added"] = GLib.DateTime.new_now_utc().to_unix()
                if getattr(preferences, "View Safe Mode").get_active() and not get_property(p, "rating", site): continue
                if any(t[:1] in get_property(p, "tags", site) for t in terms if t.startswith("-")): continue
                if not all(t in get_property(p, "tags", site) for t in terms): continue
                if any(not k[0] in p or str(get_property(p, k[0], site)) != k[1] for k in key_terms): continue
                catalog.append((p, site))
    if "random" in s:
        k = random_sort
    else:
        k = lambda c: (v := get_property(c[0], s.split("_asc")[0], c[1]), v if v else c[0]["id"])[-1]
    catalog.sort(key=k, reverse=not "_asc" in s)
    return catalog

def fetch_online_catalog(site, queries, page, count=False):
    catalog = [0, []]
    for query in queries.split("+"):
        response = json(app.session.send_and_read(Soup.Message.new("GET", sites[site]["fetch_catalog"](query, page))).get_data().decode("utf-8"))
        if count:
            n = response
            if "fetch_count" in sites[site]:
                n = app.session.send_and_read(Soup.Message.new("GET", sites[site]["fetch_count"](query))).get_data().decode("utf-8")
            if "get_count" in sites[site]:
                n = sites[site]["get_count"]((n, response))
            catalog[0] += n
        catalog[1] += sites[site]["get_catalog"](response) if "get_catalog" in sites[site] else response
    if "+" in queries: catalog[1].sort(key=lambda i: i["id"], reverse=True)
    return catalog

def finish_adding_post(s, r, st):
    b = s.send_and_read_finish(r)
    if not b: return Toast(f"Couldn't add {url}! Status: {r.get_status()}", use_markup=False)
    p = json(b.get_data().decode("utf-8"))
    p = p["post"] if "post" and "@attributes" in p else p
    p = p[0] if isinstance(p, list) else p
    if not "file_url" in p or "file_url" in sites[st]["overrides"] and not sites[st]["overrides"]["file_url"][0](p): return Toast(f"Couldn't add {url}: File URL not in post!", use_markup=False)
    p["added"] = GLib.DateTime.new_now_utc().to_unix()
    app.data["Favorites"][st].append(p)
    Toast(f"{p['id']} added to {st}'s favorites")
def general_add(url):
    if "?" in url and "tags=" in url:
        tags = GLib.Uri.parse_params(url.split("?")[-1], -1, "&", GLib.UriParamsFlags.NONE)["tags"].replace("+", " ")
        if tags in getattr(preferences, "Bookmarks").tags:
            Toast(f"{tags} already in bookmarks!")
        else:
            getattr(preferences, "Bookmarks").tags += [tags]
            Toast(f"{tags} added to bookmarks")
    else: Toast(f"Couldn't add {url}", use_markup=False)
def danbooru_add(s, url):
    if "/posts/" in url:
        p_id = url.split("?")[0].split("/posts/")[-1]
        if [i for i in app.data["Favorites"][s] if i["id"] == p_id]:
            return Toast(f"{p_id} already in {s}'s favorites!", timeout=0)
        r = app.session.send_and_read_async(Soup.Message.new("GET", f"{url.split('?')[0]}.json"), GLib.PRIORITY_DEFAULT, None, finish_adding_post, s)
    else: general_add(url)
def gelbooru_add(s, url):
    if "id=" in url:
        p_id = GLib.Uri.parse_params(url.split("?")[-1], -1, "&", GLib.UriParamsFlags.NONE)["id"]
        if [i for i in app.data["Favorites"][s] if i["id"] == p_id]:
            return Toast(f"{p_id} already in {s}'s favorites!")
        r = app.session.send_and_read_async(Soup.Message.new("GET", sites[s]["fetch_catalog"](f"id:{p_id}", 1)), GLib.PRIORITY_DEFAULT, None, finish_adding_post, s)
    else: general_add(url)
def moebooru_add(s, url):
    if "/post/show/" in url:
        p_id = url.split("?")[0].split("/post/show/")[-1].split("/")[0]
        if [i for i in app.data["Favorites"][s] if i["id"] == p_id]:
            return Toast(f"{p_id} already in {s}'s favorites!", timeout=0)
        r = app.session.send_and_read_async(Soup.Message.new("GET", sites[s]["fetch_catalog"](f"id:{p_id}", 1)), GLib.PRIORITY_DEFAULT, None, finish_adding_post, s)
    else: general_add(url)

for i in ("Danbooru", "AI Booru"):
    sites[i]["add"] = danbooru_add
    sites[i]["fetch_catalog"] = lambda t, p, _i=i: f"{sites[_i]['url']}/posts.json?limit={limit}&page={p}&tags={t + (' status:any' if not 'status:' in t else '') + (' rating:safe' if getattr(preferences, 'View Safe Mode').get_active() else '')}" + (sites[_i]["api"]() if "api" in sites[_i] else "")
    sites[i]["get_catalog"] = lambda c: tuple(i for i in c if "file_url" in i and not i["file_url"].endswith("swf"))
    sites[i]["fetch_count"] = lambda t, _i=i: f"{sites[_i]['url']}/counts/posts.json?tags={t}"
    sites[i]["get_count"] = lambda d: (c := json(d[0]), c["counts"]["posts"] if c["counts"]["posts"] else 0)[1]
    sites[i]["get_url"] = lambda q, _i=i: f"{sites[_i]['url']}/posts/{q[0]['id']}" if isinstance(q[0], dict) else f"{sites[_i]['url']}/posts?page={q[1]}&tags={q[0] + (' status:any' if not 'status:' in q[0] else '') + (' rating:safe' if getattr(preferences, 'View Safe Mode').get_active() else '')}"
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
    sites[i]["fetch_catalog"] = lambda t, p, _i=i: f"{sites[_i]['url']}/index.php?limit={limit}&pid={p - 1}&page=dapi&s=post&q=index&tags={t + (' rating:general' if getattr(preferences, 'View Safe Mode').get_active() else '')}&json=1" + (sites[_i]["api"]() if "api" in sites[_i] else "")
    sites[i]["get_catalog"] = lambda c: c["post"] if "post" in c else []
    sites[i]["get_count"] = lambda c: c[1]["@attributes"]["count"]
    sites[i]["get_url"] = lambda q, _i=i: f"{sites[_i]['url']}/index.php?page=post&s=view&id={q[0]['id']}" if isinstance(q[0], dict) else f"{sites[_i]['url']}/index.php?page=post&s=list&pid={q[1] - 1}&tags={q[0] + (' rating:general' if getattr(preferences, 'View Safe Mode').get_active() else '')}"
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
    sites[i]["fetch_catalog"] = lambda t, p, _i=i: f"{sites[_i]['url']}/post.json?limit={limit}&page={p}&tags={t + (' rating:general' if getattr(preferences, 'View Safe Mode').get_active() else '')}&json=1" + (sites[_i]["api"]() if "api" in sites[_i] else "")
    sites[i]["get_catalog"] = lambda c: c[1]
    sites[i]["fetch_count"] = lambda t, _i=i: f"{sites[_i]['url']}/post.xml?tags={t}"
    sites[i]["get_count"] = lambda c: int(c[0].split('<posts count="')[1].split(' offset="')[0].strip('"'))
    sites[i]["get_url"] = lambda q, _i=i: f"{sites[_i]['url']}/post?id={q[0]['id']}" if isinstance(q[0], dict) else f"{sites[_i]['url']}/post?page={q[1]}&tags={q[0] + (' rating:general' if getattr(preferences, "View Safe Mode").get_active() else '')}"
    sites[i]["overrides"] = {
        "hash": lambda p: p["md5"],
        "size": lambda p: f"{p['width']}x{p['height']} ({GLib.format_size(p['file_size'])})",
        "uploader": lambda p: p["author"],
        "tags": (lambda p: p["tags"].split(" "), lambda t: " ".join(t)),
        "rating": (lambda p: ratings.index(next(i for i in ratings if i.lower().startswith(p["rating"]))), lambda n: ratings[n].lower()[:1]),
        "parent_id": (lambda p: 0 if p["parent_id"] is None else p["parent_id"], lambda v: None if int(v) == 0 else int(v)),
        "created_at": (lambda p: GLib.DateTime.new_from_unix_utc(p["created_at"]), lambda d: d.to_utc().to_unix()),
    }

for i in sites:
    if "api" in sites[i]: app.data["Accounts"].setdefault(i, {"User": "", "Token": ""} )
    app.data["Favorites"].setdefault(i, [])

get_md5 = lambda b: (c := GLib.Checksum.new(0), c.update(b.get_data()), c.get_string())[-1]
fail_url = lambda u, e=None: Toast(f"{u}\nError: {e}" if e else f"\n{u} could not be added!", use_markup=False)
def probe(url):
    p = Gio.Subprocess.new(("ffprobe", "-v", "quiet", "-show_entries", "stream=width,height:format=size,duration", "-of", "json", "-i", url), Gio.SubprocessFlags.STDOUT_PIPE)
    p.wait()
    try:
        o = json(p.get_stdout_pipe().read_bytes(8192).get_data())
        if not "streams" in o: return Toast(f"No valid stream in {url}")
        i = o["streams"][0]
        i["duration"] = int(float(o["format"].get("duration", 0)))
        i["size"] = int(o["format"].get("size", 0))
        i["file_url"] = url
        return i
    except Exception as e: return Toast(f"URL: {url}\nError: {e}")
def add_favorite(p):
    now = GLib.DateTime.new_now_utc().to_unix()
    for k, v in (("id", max((i["id"] for i in app.data["Favorites"]["Favorites"]), default=0) + 1), ("width", 0), ("height", 0), ("duration", 0), ("rating", 0), ("source", ""), ("has_children", False), ("parent_id", 0), ("tags", []), ("added", now), ("created_at", now), ("updated_at", now), ("file_url", ""), ("preview_url", ""), ("hash", ""), ("size", 0)): p.setdefault(k, v)
    if not p["file_url"].startswith("http"):
        p["file_url"] = f"file://{p['file_url']}"
    app.data["Favorites"]["Favorites"].append(p)
    Toast(f"Post {p['id']} added to favorites!")
    return p
def add_from_url(s, r, fun, url):
    b = s.send_and_read_finish(r)
    if not b: fail_url(url)
    try: fun(b, url)
    except Exception as e: fail_url(url, e)
def zerochan_add(b, url):
    p = json(b.get_data().decode("utf-8"))
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
        p["hash"] = get_md5(app.session.send_and_read(Soup.Message.new("GET", file_url)))
        add_favorite(p)
def chan_add(b, url):
    if "warosu" in url:
        response = b.get_data().decode("utf-8")
        p = url.rsplit("/", 1)[-1].split("#p")[-1]
        file_url = response.split(f"alt={p}")[0].rsplit("href=", 1)[1].split(">")[0]
        thumbnail_url = file_url.replace("img", "thumb").rsplit("/", 1)[0] + "/" + file_url.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "s.jpg"
        b = app.session.send_and_read(Soup.Message.new("GET", file_url))
    else:
        file_url = url.replace("thumb", "image").replace("s.", ".")
        thumbnail_url = file_url.replace("image", "thumb").rsplit("/", 1)[0] + "/" + file_url.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "s.jpg"
    p = probe(file_url)
    p["hash"], p["source"], p["preview_url"], p["created_at"] = get_md5(b), url, thumbnail_url, int(file_url.rsplit("/", 1)[-1].split(".")[0][:10])
    add_favorite(p)
def artstation_add(b, url):
    res = json(b.get_data().decode("utf-8"))
    created_at, updated_at = GLib.DateTime.new_from_iso8601(res["created_at"]).to_utc().to_unix(), GLib.DateTime.new_from_iso8601(res["updated_at"]).to_utc().to_unix()
    tags = res["tags"] + res["title"].split(" ") + res["user"]["username"].split(" ")
    for i in res["assets"]:
        file_url = i["image_url"]
        for it in ("/small/", "/large/", "/medium/"):
            file_url = file_url.replace(it, "/4k/")
        p = probe(file_url)
        b = app.session.send_and_read(Soup.Message.new("GET", file_url))
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
        b = app.session.send_and_read(Soup.Message.new("GET", i))
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
    post = json(b.get_data().decode("utf-8"))
    created_at, updated_at = tuple(GLib.DateTime.new_from_iso8601(post["post"][i], GLib.TimeZone.new_utc()) for i in ("published", "edited"))
    for i in post["previews"]:
        if not Gio.content_type_guess(i["name"])[0].startswith(("video", "image")): continue
        file_url = f'{i["server"]}/data{i["path"]}'
        p = probe(file_url)
        p["hash"], p["source"], p["preview_url"] = i["path"].split("/")[-1].split(".")[0], url, f'https://img.kemono.cr/thumbnail/data{i["path"]}'
        add_favorite(p)
extra = {"Zerochan": (lambda u: u.startswith("https://www.zerochan.net/") and u.split("/")[-1].isdigit(), lambda u: app.session.send_and_read_async(Soup.Message.new("GET", f"{u}?&json"), GLib.PRIORITY_DEFAULT, None, add_from_url, *(zerochan_add, u))),
        "Twitter": (lambda u: u.replace("https://", "").startswith(("xcancel.com", "twitter.com", "x.com", "nitter.net", "cdn.xcancel.com", "pbs.twimg.com")), lambda u: (url := u.replace("x.com", "nitter.net").replace("xcancel.com", "nitter.net").replace("twitter.com", "nitter.net"), app.session.send_and_read_async((m := Soup.Message.new("GET", url), tuple(m.get_request_headers().append(k, v) for k, v in (("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"), ("Accept-Language", "en-US,en;q=0.5"), ("Sec-Fetch-Dest", "document"))), m)[-1], GLib.PRIORITY_DEFAULT, None, add_from_url, *(twitter_add, url)))),
        "4chan": (lambda u: u.replace("https://", "").startswith(("boards.4chan.org", "warosu.org", "desu-usergeneratedcontent.xyz")), lambda u: (url := u.replace("boards.4chan", "warosu") if "boards.4chan" in u and u.split("/")[3].startswith(("3", "biz", "cgl", "ck", "diy", "fa", "ic", "jp", "lit", "sci", "vr", "vt")) else u, app.session.send_and_read_async(Soup.Message.new("GET", url), GLib.PRIORITY_DEFAULT, None, add_from_url, *(chan_add, url)))),
        "Artstation": (lambda u: "artstation.com/artwork/" in u, lambda u: app.session.send_and_read_async(Soup.Message.new("GET", f"{u.replace('artwork', 'projects')}.json"), GLib.PRIORITY_DEFAULT, None, add_from_url, *(artstation_add, u))),
        "Reddit": (lambda u: u.startswith("https://www.reddit.com/r/") and "/comments/" in u, lambda u: app.session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, add_from_url, *(reddit_add, u))),
        "Pinterest": (lambda u: "pinterest.com/pin/" in u, lambda u: app.session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, add_from_url, *(pinterest_add, u))),
        "Kemono": (lambda u: u.startswith("https://kemono.cr") and "user" in u and "post" in u, lambda u: app.session.send_and_read_async((m := Soup.Message.new("GET", u.replace(".cr", ".cr/api/v1/")), m.get_request_headers().append("Accept", "text/css"), m)[-1], GLib.PRIORITY_DEFAULT, None, add_from_url, *(kemono_add, u))),
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
                b = app.session.send_and_read(Soup.Message.new("GET", url))
                p["hash"], p["source"], p["preview_url"] = get_md5(b), url, url
                add_favorite(p)
                continue
            except Exception as e:
                fail_url(url, e)
                continue
            fail_url(url)
    if isinstance(v, Gdk.Texture):
        f, md5 = app.data_folder.get_child(f"{md5}.png"), get_md5(v.save_to_png_bytes())
        v.save_to_png(f.peek_path())
        return add(Gdk.FileList.new_from_list((f,)))
    if isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            if not Gio.content_type_guess(file.get_basename())[0].startswith(("video", "image")):
                fail_url(file.peek_path())
                continue
            b = file.load_bytes()[0]
            md5 = get_md5(b)
            f, pr = app.data_folder.get_child(f"{md5}.{file.peek_path().split('.')[-1]}"), app.data_folder.get_child(f"preview-{md5}.webp")
            p = probe(file.peek_path())
            if not p: return fail_url(file.peek_path())
            generate_thumbnail(file, pr)
            if not f.equal(file): file.copy(f, Gio.FileCopyFlags.NONE)
            p["hash"], p["source"], p["file_url"], p["preview_url"] = md5, file.get_uri(), f.get_uri(), pr.get_uri()
            add_favorite(p)
file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))
Action("add-file", lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.window, None, lambda d, r: add(d.open_multiple_finish(r))), "<primary><shift>a")
add_url = EntryDialog(heading="Add URL to Bookmarks/Favorites", callback=lambda d: add(d.get_extra_child().get_buffer().get_property("text")), multiline=True)
Action("add-url", lambda *_: add_url.present(app.window), "<primary><shift>d")

def tag_widget_added(r, tag):
    for n in range(3):
        e = Gtk.GestureClick(button=n + 1)
        e.connect("pressed", tag_clicked)
        tag.get_first_child().add_controller(e)

preferences = Adw.PreferencesDialog(search_enabled=True, content_width=530, content_height=600)
Action("preferences", lambda *_: preferences.present(app.window), "<primary>p")
for p in app.data:
    if p in ("Window", "Favorites", "Tabs"): continue
    page = Adw.PreferencesPage(title=p, icon_name="preferences-system-symbolic" if p == "General" else "tag-outline-symbolic" if p == "Tags" else "folder-user-symbolic" if p == "Accounts" else "")
    for g in app.data[p]:
        group = Adw.PreferencesGroup(title=g)
        if p == "Tags":
            r = TagRow(title=g)
            r.connect("tag-widget-added", tag_widget_added)
            r.tags = app.data[p][g]
            r.property = "tags"
            r.path = p
            group.add(r)
            app.persist.append(r)
            setattr(preferences, g, r)
        else:
            for n, v in app.data[p][g].items():
                r = Adw.ComboRow(model=Gtk.StringList.new(tuple(sites)), selected=tuple(sites).index(v)) if n == "New Tab Site" else Adw.SwitchRow(active=v) if type(v) is bool else Adw.EntryRow(text=v)
                r.set_title(n)
                r.page, r.group, r.property = p, g, "active" if isinstance(r, Adw.SwitchRow) else "text" if isinstance(r, Adw.EntryRow) else "selected-item" 
                app.persist.append(r)
                group.add(r)
                setattr(preferences, f"{g} {n}", r)
        page.add(group)
    preferences.add(page)

search_popover = Gtk.Popover(child=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=("boxed-list",)))
site_row, page_row = Adw.ComboRow(title="Site", model=Gtk.StringList.new(tuple(sites))), Adw.SpinRow.new_with_range(1, 1000, 1)
site_row.get_template_child(Adw.ComboRow, "popover").connect("closed", lambda *_: search_popover.popdown())
site_row.connect("notify::selected", lambda *_: search_popover.popdown())
page_row.set_title("Page")
for i in (site_row, page_row): search_popover.get_child().append(i)
search_box = Gtk.Box(css_name="search")
search_box.append(Button(t=Gtk.MenuButton, icon_name="view-more", tooltip_text="More", popover=search_popover))
search = Gtk.Text(placeholder_text="Search", hexpand=True)
search_list = Gtk.ListBox()
def select_suggestion(l, r):
    if not r: return
    app.modifying = True
    nt, p = search_current_word(r.get_child().i["value"])
    search.set_text(nt)
    search.set_position(p)
    app.modifying = False
search_list.connect("row-selected", select_suggestion)
search_list.connect("row-activated", lambda l, r: (select_suggestion(l, r), do_search()))
suggestions_popover = Gtk.Popover(child=Gtk.ScrolledWindow(child=search_list, hexpand=True, max_content_width=365, propagate_natural_height=True, propagate_natural_width=True, valign=Gtk.Align.START, width_request=300), autohide=False, can_focus=False, halign=Gtk.Align.CENTER, has_arrow=False, hexpand=True, valign=Gtk.Align.START)
suggestions_popover.set_parent(search)
def search_current_word(v=None):
    q = search.get_text().split(" ")
    length, closest_index = 0, -1
    for i, word in enumerate(i for i in q):
        length += len(word) + 1
        if length > search.get_position():
            closest_index = i
            if i > 0 and (search.get_position() - (length - len(word) - 1)) < (length - search.get_position()):
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
    for i in json(response.get_data().decode("utf-8")):
        box = Gtk.Box()
        box.append(Gtk.Label(label=f"{i['antecedent']} → {i['label']}" if "antecedent" in i else i["label"]))
        if "post_count" in i: box.append(Gtk.Label(css_classes=("dimmed",), label=f"({i['post_count']})"))
        box.i = i
        GLib.idle_add(search_list.append, box)
    app.modifying = False
    GLib.idle_add(suggestions_popover.popup)
    if not search_list.get_first_child(): GLib.idle_add(suggestions_popover.popdown)
def search_changed(*_):
    if app.modifying or not search.get_text() or not getattr(preferences, "View Autocomplete").get_active(): return
    app.modifying = True
    m = Soup.Message.new("GET", f"{sites['Danbooru']['url']}/autocomplete.json?search[query]={search_current_word()}&search[type]=tag_query&limit=15")
    response = app.session.send_and_read_async(m, GLib.PRIORITY_DEFAULT, None, search_suggestions)
search.connect("notify::text", search_changed)
def search_move(a, b, direction):
    if suggestions_popover.get_mapped():
        selected = search_list.get_selected_row()
        new = (selected.get_prev_sibling() if direction == Gtk.DirectionType.UP and selected else selected.get_next_sibling() if direction == Gtk.DirectionType.DOWN and selected else search_list.get_first_child())
        if new == None:
            new = search_list.get_first_child() if direction == Gtk.DirectionType.DOWN else search_list.get_last_child()
        search_list.select_row(new)
        return True
search.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Up"), Gtk.CallbackAction.new(search_move, Gtk.DirectionType.UP)))
search.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Down"), Gtk.CallbackAction.new(search_move, Gtk.DirectionType.DOWN)))
search_box.append(search)
def do_search(*_):
    suggestions_popover.popdown()
    if hasattr(view.get_selected_page().get_child().get_child(), "q"): del view.get_selected_page().get_child().get_child().q
    app.thread.submit(tab_load, q=[search.get_text(), int(page_row.get_value()), site_row.get_selected_item().get_string(), ()])
search.connect("activate", do_search)
search_box.append(Button(icon_name="edit-find", tooltip_text="Search", callback=do_search))
view = Adw.TabView(focusable=True)
def tab_history(b):
    view.get_selected_page().index += (1 if "next" in b.get_icon_name() else -1)
    view.get_selected_page().history[view.get_selected_page().index][3] = []
    app.thread.submit(tab_load)
multi = Adw.MultiLayoutView()
menu = Menu((("Add a URL", "add-url"), ("Add Files to Favorites", "add-file")),
            (("Fullscreen", "fullscreen"), ("View Open Tabs", "overview"), ("Reopen Closed Tab", "reopen-tab"), ("Preferences", "preferences")), app.default_menu)
for i, w in (("view", view), ("search", search_box),
            ("previous", Button(icon_name="go-previous", tooltip_text="Back", callback=tab_history)),
            ("next", Button(icon_name="go-next", tooltip_text="Forward", callback=tab_history)),
            ("menu", Button(t=Gtk.MenuButton, menu_model=menu, tooltip_text="Menu", icon_name="open-menu"))):
    multi.set_child(i, w)
wide, wide_header = Adw.ToolbarView(content=Adw.LayoutSlot.new("view")), Adw.HeaderBar(title_widget=Adw.Clamp(hexpand=True, child=Adw.LayoutSlot.new("search"), maximum_size=400))
for i in (wide_header, Adw.TabBar(view=view)): wide.add_top_bar(i)
narrow, narrow_header = Adw.ToolbarView(content=Adw.LayoutSlot.new("view")), Adw.HeaderBar(show_title=False, show_end_title_buttons=False)
for i in (Adw.LayoutSlot.new("search"), narrow_header): narrow.add_bottom_bar(i)
wide.bind_property("reveal-top-bars", narrow, "reveal-bottom-bars", GObject.BindingFlags.DEFAULT)
Action("fullscreen", lambda *_: wide.set_reveal_top_bars(not wide.get_reveal_top_bars()), "F11")
for i, n in ((wide, "wide"), (narrow, "narrow")): multi.add_layout(Adw.Layout(content=i, name=n))
for i in ("previous", "next"): (wide_header.pack_start(Adw.LayoutSlot.new(i)), narrow_header.pack_start(Adw.LayoutSlot.new(i)))
for i in ("menu",): (wide_header.pack_end(Adw.LayoutSlot.new(i)), narrow_header.pack_end(Adw.LayoutSlot.new(i)))
wide_header.pack_start(Button(icon_name="tab-new", tooltip_text="New Tab", action_name="app.new-tab"))
narrow_header.pack_start(Adw.TabButton(view=view, action_name="app.overview"))
overview = Adw.TabOverview(child=multi, enable_new_tab=True, view=view, secondary_menu=menu)
Action("overview", lambda *_: overview.set_open(not overview.get_open()), "<primary><shift>o")
app.window.get_content().set_child(overview)
overview_drop = Gtk.DropTarget(preload=True, actions=Gdk.DragAction.COPY, formats=Gdk.ContentFormats.parse("GdkTexture GdkFileList GFile"))
def paste():
    c = app.window.get_display().get_clipboard()
    if c.get_formats().contain_gtype(Gdk.Texture):
        c.read_texture_async(None, lambda cl, r: add(cl.read_texture_finish(r)))
        return True
    elif c.get_formats().contain_gtype(Gdk.FileList):
        c.read_value_async(Gdk.FileList, 0, None, lambda cl, r: add(cl.read_value_finish(r)))
        return True
overview_drop.connect("drop", lambda d, v, *_: add(v))
overview.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<primary>v"), Gtk.CallbackAction.new(paste)))
overview.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Escape"), Gtk.CallbackAction.new(lambda *_: suggestions_popover.popdown())))
overview.add_controller(overview_drop)
file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))
_breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(Adw.BreakpointConditionLengthType.MAX_WIDTH, 700, Adw.LengthUnit.PX))
app.window.add_breakpoint(_breakpoint)
_breakpoint.add_setter(multi, "layout-name", "narrow")

def tag_clicked(e, *_):
    q = view.get_selected_page().history[view.get_selected_page().index]
    match e.get_button():
        case 1: app.thread.submit(tab_load, q=[e.get_widget().get_label(), 1, q[2], ()])
        case 2: Tab(q=e.get_widget().get_label(), s=q[2])
        case 3:
            if e.get_widget().get_ancestor(TagRow) != getattr(preferences, "Blacklist"):
                t = f"{e.get_widget().get_label()} "
                if e.get_widget().get_label() in getattr(preferences, "Blacklist").tags:
                    t += "removed from "
                    getattr(preferences, "Blacklist").tags = [i for i in getattr(preferences, "Blacklist").tags if not i == e.get_widget().get_label()]
                else:
                    t += "added to "
                    getattr(preferences, "Blacklist").tags = getattr(preferences, "Blacklist").tags + [e.get_widget().get_label()]
            Toast(t + "blacklist", timeout=2)
def show_revealer(e, *_):
    p = e.get_widget()
    if tuple(i for i in app.data["Favorites"][p.s] if i["id"] == p.o["id"]): p.favorite.set_properties(tooltip_text="Remove Favorite", icon_name="starred-symbolic")
    else: p.favorite.set_properties(tooltip_text="Add Favorite", icon_name="star-new-symbolic")
    p_id = get_property(p.o, "parent_id", p.s)
    has_c = get_property(p.o, "has_children", p.s)
    tt = "Has Parent" if p_id else "Has Children"
    i = "folder-user" if p_id else "preferences-system-parental-controls"
    if p_id and has_c:
        tt, i = "Has Parent and Children", "system-users"
    p.related.set_properties(tooltip_text=tt, icon_name=f"{i}-symbolic", visible=int(p_id) > 0 or has_c)
def post_related(b):
    p = b.get_ancestor(Gtk.Overlay)
    p_id = get_property(p.o, "parent_id", p.s)
    has_c = get_property(p.o, "has_children", p.s)
    if p_id: Tab(q=f"parent:{p_id}", s=p.s)
    if has_c: Tab(q=f"parent:{p.o['id']}", s=p.s)
def post_favorite(b):
    p = b.get_ancestor(Gtk.Overlay)
    if tuple(i for i in app.data["Favorites"][p.s] if i["id"] == p.o["id"]):
        app.data["Favorites"][p.s] = [i for i in app.data["Favorites"][p.s] if i["id"] != p.o["id"]]
    else:
        p.o["added"] = GLib.DateTime.new_now_utc().to_unix()
        app.data["Favorites"][p.s].append(p.o)
        if getattr(preferences, "Favorites Download Favorites").get_active(): post_download(p)
    show_revealer(p.event)
def finish_func(picture, paintable):
    if not isinstance(picture.get_parent(), Gtk.Overlay):
        paintable.colors = palette(paintable, distance=1.6, black_white=3.0)
        GLib.idle_add(apply_colors)
Action("more", lambda *_: view.get_selected_page().get_child().get_child().more.emit("clicked") if hasattr(view.get_selected_page().get_child().get_child(), "more") else None, "<primary>e")
def Post(o, s, p=False):
    _hash = get_property(o, "hash", s)
    file_url, preview_url = tuple(get_property(o, i, s) or "" for i in ("file_url", "preview_url"))
    uri = preview_url if (p or not file_url) else file_url
    file, preview_file = tuple(app.data_folder.get_child(i) for i in (f"{_hash}.{file_url.rsplit('.')[-1]}", f"preview-{_hash}.{preview_url.rsplit('.')[-1]}"))
    fe, pe = tuple(os.path.exists(i.peek_path()) for i in (file, preview_file))
    uri = preview_file if pe and (p or not fe) else file if fe else uri
    if uri == "":
        uri = None
    post = Media(uri, finish_func=finish_func, parent_type=Gtk.Overlay, play=not p, scrollable=int(not getattr(preferences, "View Constrain Post Size").get_active()) if not p else None, c__halign=Gtk.Align.FILL if p else Gtk.Align.CENTER)
    buttons = tuple(Button(name=n, callback=c) for n, c in (("related", post_related), ("favorite", post_favorite), ("more", show_edit)))
    for i in buttons: setattr(post, i.get_name(), i)
    post.more.set_properties(icon_name="view-more", tooltip_text="More")
    revealer = Gtk.Revealer(child=Gtk.Box(), halign=Gtk.Align.END, valign=Gtk.Align.START, transition_type=Gtk.RevealerTransitionType.CROSSFADE)
    post.event.bind_property("contains-pointer", revealer, "reveal-child", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, toggle_revealer)
    post.add_overlay(revealer)
    if p:
        post.height = max(get_property(o, "height", s), 1) / max(get_property(o, "width", s), 1)
        duration = get_property(o, "duration", s)
        if duration: GLib.idle_add(post.add_overlay, Gtk.Label(valign=Gtk.Align.END, halign=Gtk.Align.START, label=duration[3:] if duration.startswith("00:") else duration))
    else:
        post.get_child().get_child().set_properties(overflow=False, valign=Gtk.Align.CENTER)
        revealer.get_child().add_css_class("linked")
    for i in buttons: GLib.idle_add(revealer.get_child().append, i)
    post.file, post.preview_file = file, preview_file
    post.p, post.o, post.s = p, o, s
    post.event.connect("enter", show_revealer)
    if uri and not (fe and pe) and getattr(preferences, "Favorites Download Favorites").get_active() and o in app.data["Favorites"][s]: post_download(post)
    return post

def catalog_activate(m, c, b):
    match b:
        case 1: tab_load(q=[c.o, 1, c.s, []])
        case 2: Tab(q=c.o, s=c.s)
        case 3: c.favorite.emit("clicked")
def catalog_load_more(sw, p):
    content = sw.get_parent()
    if p == 3 and not content.count[0] >= content.count[1]:
        t = view.get_page(content.get_ancestor(Adw.Bin))
        if not t.get_loading(): app.thread.submit(tab_load, t=t, page=True)
def tab_changed(*_):
    GLib.idle_add(apply_colors)
    v = view.get_selected_page()
    if not hasattr(v, "history"): return
    multi.get_child("previous").set_sensitive(len(v.history) - 1 >= v.index and v.index != 0 ) 
    multi.get_child("next").set_sensitive(len(v.history) > v.index + 1) 
    q = v.history[v.index]
    site_row.set_selected(tuple(sites).index(q[2]))
    page_row.set_value(q[1])
    if not isinstance(q[0], list):
        app.modifying = True
        search.set_text(f"id:{q[0]['id']}" if isinstance(q[0], dict) else q[0])
        app.modifying = False
        search.set_position(-1)
    content = v.get_child().get_child()
    if v.get_loading() or isinstance(content, Adw.Spinner) or hasattr(content, "q") and content.q == q: return
    app.thread.submit(tab_load)
view.connect("notify::selected-page", tab_changed)
app.closed = []
reopen_action = Action("reopen-tab", lambda *_: (q := app.closed.pop(-1), Tab(q=q[0], p=q[1], s=q[2]), reopen_action.set_enabled(bool(app.closed))) if app.closed else None, "<primary><shift>t")
reopen_action.set_enabled(bool(app.closed))
def tab_operation(a, b=False, t=False):
    if not t:
        t = view.t if "context" in a.get_name() and isinstance(a, Gio.SimpleAction) else b if isinstance(b, Adw.TabPage) else view.get_selected_page()
    if (isinstance(a, Adw.TabView) or (isinstance(a, Gio.SimpleAction) and "close" in a.get_name())):
        if t.get_pinned(): return
        else:
            view.close_page(t) if isinstance(a, Gio.SimpleAction) else None
            app.closed.append(t.history[t.index])
            if hasattr(t.get_child().get_child(), "favorite"):
                paintable = t.get_child().get_child().get_child().get_child().get_child().get_paintable()
                if hasattr(paintable, "clear"):
                    paintable.pause()
                    paintable.clear()
                del paintable
            reopen_action.set_enabled(bool(app.closed))
        return
    q = t.history[t.index]
    if "open-current" in a.get_name(): return launch(sites[q[2]]["get_url"](q))
    if isinstance(q[0], dict) and not hasattr(t.get_child().get_child(), "favorite"):
        tab_load(t)
        return GLib.idle_add(lambda *_: tab_operation(a, t=t))
    if hasattr(t.get_child().get_child(), "favorite"):
        if "favorite" in a.get_name(): t.get_child().get_child().favorite.emit("clicked")
    else:
        if "favorite" in a.get_name():
            q = q[0]
            getattr(preferences, "Bookmarks").tags = [i for i in getattr(preferences, "Bookmarks").tags if not i == q] if q in getattr(preferences, "Bookmarks").tags else [i for i in getattr(preferences, "Bookmarks").tags] + [q]
            Toast(f"{q} {'added to' if q in getattr(preferences, 'Bookmarks').tags else 'removed from'} bookmarks", timeout=3)
view.connect("close-page", tab_operation)
for n, k in (("favorite", "d"), ("close", "w"), ("open-current", "o")): (Action(n, tab_operation, f"<primary>{k}"), Action("context-" + n, tab_operation))
Action("context-pin", lambda *_: view.set_page_pinned(view.t, not view.t.get_pinned()))
def tab_setup_menu(v, t):
    v.t = t
    if not v.t: return
    q = v.t.history[v.t.index]
    v.get_menu_model().remove_all()
    tab_menu, tab_context_menu = Gio.Menu.new(), Gio.Menu.new()
    tab_context_menu.append("Open in Browser", "app.context-open-current")
    tab_context_menu.append(("Remove Favorite" if tuple(i for i in app.data["Favorites"][q[2]] if i["id"] == q[0]["id"]) else "Add Favorite") if isinstance(q[0], dict) else ("Remove Bookmark" if q[0] in getattr(preferences, "Bookmarks").tags else "Add Bookmark"), "app.context-favorite")
    tab_menu.append("Unpin Tab" if v.t.get_pinned() else "Pin Tab", "app.context-pin")
    tab_menu.append("Close Tab", "app.context-close")
    for i in (tab_context_menu, tab_menu): v.get_menu_model().append_section(None, i)
view.set_menu_model(Gio.Menu.new())
view.connect("setup-menu", tab_setup_menu)
def tab_load(t=None, page=False, q=[]):
    GLib.idle_add(suggestions_popover.popdown)
    t = t if t else view.get_selected_page()
    content = t.get_child().get_child()
    if q:
        t.index = len(t.history)
        t.history.append(q)
    q = t.history[t.index]
    if content and not page and hasattr(content, "q") and content.q == q: return
    if page and not (q[3] and q[2] != "Favorites"):
        q[1] += 1
    if t == view.get_selected_page():
        GLib.idle_add(multi.get_child("previous").set_sensitive, len(t.history) - 1 >= t.index and t.index != 0) 
        GLib.idle_add(multi.get_child("next").set_sensitive, len(t.history) > t.index + 1)
    GLib.idle_add(app.window.remove_css_class, "colored")
    if q[3]:
        catalog = q[3][:limit]
    else:
        if isinstance(q[0], str):
            if not page: GLib.idle_add(t.get_child().set_child, Adw.Spinner())
            GLib.idle_add(t.set_loading, True)
            if q[2] == "Favorites":
                q[3] = fetch_favorite_catalog(q[0])
                count, q[3] = len(q[3]), q[3][limit * q[1]:] if q[1] > 1 else q[3]
            else:
                try:
                    count, q[3] = fetch_online_catalog(q[2], q[0], q[1], not page)
                except Exception as e:
                    Toast(e)
                    GLib.timeout_add(200, t.set_loading, False)
                    return GLib.idle_add(t.get_child().set_child, Adw.StatusPage(description=f"{e}", icon_name="dialog-error-symbolic", title="Error!"))
            catalog = q[3][:limit]
            if not page: GLib.idle_add(t.set_title, f"{q[0]} ({count}) ({q[2]})")
        elif isinstance(q[0], dict):
            catalog = (q[0],)
    q[3] = tuple(i for i in q[3] if not i in catalog)
    if not catalog and not page:
        content = Adw.StatusPage(description=f"No posts for page {q[1]}\nTry a different search", icon_name="edit-find-symbolic", title="No Results")
    elif len(catalog) == 1 and not page:
        content = Post(catalog[0][0] if isinstance(catalog[0], tuple) else catalog[0], catalog[0][1] if isinstance(catalog[0], tuple) else q[2])
        m = f"post {content.o['id']} ({content.s})"
        print(f'{GLib.DateTime.new_now_local().format("%R")} in {m}')
        GLib.idle_add(t.set_title, m)
    else:
        if page:
            content.count[0] += len(catalog)
        else:
            content = MasonryBox(activate=catalog_activate)
            t.viewport = content.get_child()
            content.count = [len(catalog), count]
            content.get_child().connect("edge-reached", catalog_load_more)
        for i in catalog:
            if any(it in get_property(i, "tags", i[1]) for it in getattr(preferences, "Blacklist").tags): continue
            GLib.idle_add(content.add, Post(i[0] if q[2] == "Favorites" else i, i[1] if q[2] == "Favorites" else q[2], True))
        total_pages = -(-content.count[1] // limit)
        m = f"Page {q[1]} of {total_pages}"
        Toast(m, message=f'{GLib.DateTime.new_now_local().format("%R")} in {q[2]} "{q[0]}" {m}', timeout=2)
    content.q = q
    GLib.idle_add(t.get_child().set_child, content)
    GLib.timeout_add(200, t.set_loading, False)
    GLib.timeout_add(200, suggestions_popover.popdown)
    if t.get_child().get_mapped():
        GLib.idle_add(site_row.set_selected, tuple(sites).index(q[2])) 
        GLib.idle_add(page_row.set_value, q[1])
def Tab(*_, q=None, p=1, s=""):
    tab = view.add_page(Adw.Bin())
    q, s = getattr(preferences, "Tabs New Tab Query").get_text() if q == None else q, s if s else getattr(preferences, "Tabs New Tab Site").get_selected_item().get_string()
    tab.set_title(f"post {q['id']} ({s})" if isinstance(q, dict) else f"{q} ({s})")
    tab.history, tab.index = [[q, p, s, ()]], 0
    return tab
Action("new-tab", Tab, "<primary>t")
overview.connect("create-tab", Tab)

edit = Adw.PreferencesDialog(content_height=530, content_width=530, search_enabled=True)
pages = (Adw.PreferencesPage(icon_name="tag-outline-symbolic", title="Tags"), Adw.PreferencesPage(icon_name="document-edit-symbolic", title="Edit"), Adw.PreferencesPage(icon_name="help-about-symbolic", title="Info"))
for i in pages: edit.add(i)
group = Adw.PreferencesGroup()
def post_finish_download(a, r, d):
    b = a.send_and_read_finish(r)
    if b: d[1].replace_contents_bytes_async(b, None, False, 0)
    if d[0].get_root():
        t = view.get_page(d[0].get_ancestor(Adw.Bin))
        GLib.idle_add(t.set_loading, False)
    map_download()
def post_download(p):
    if os.path.exists(p.file.peek_path()) and os.path.exists(p.preview_file.peek_path()):
        launch(p.preview_file if p.p else p.file, folder=True)
    else:
        view.get_selected_page().set_loading(True)
        for f, u in ((p.preview_file, get_property(p.o, "preview_url", p.s)), (p.file, get_property(p.o, "file_url", p.s))):
            Toast(f"Downloading {u}", timeout=1)
            app.session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, post_finish_download, (p, f))
Action("download", lambda *_: post_download(view.get_selected_page().get_child().get_child()) if hasattr(view.get_selected_page().get_child().get_child(), "favorite") else None, "<primary>s")
download = Adw.ButtonRow()
download.add_css_class("suggested-action")
map_download = lambda: download.set_title("Open" if os.path.exists(edit.p.preview_file.peek_path()) and os.path.exists(edit.p.file.peek_path()) else "Download")
download.connect("activated", lambda *_: post_download(edit.p))
group.add(download)
pages[1].add(group)
dates = tuple(DateRow(title=i.title().split(" || ")[0].replace("_", " "), name=i) for i in ("added", "created_at", "updated_at || changed"))
rating_group = Adw.ToggleGroup(name="rating", valign=Gtk.Align.CENTER)
editable = ((TagRow(name="tags || tag_string", title="Tags"), "tags"),
            (Adw.EntryRow(title="Source", name="source"), "text"),
            (Adw.EntryRow(title="File URL", name="file_url"), "text"),
            (Adw.EntryRow(title="Preview URL", name="preview_url || preview_file_url"), "text"),
            (rating_group, "active"),
            (Adw.SpinRow(title="Parent ID", name="parent_id", adjustment=Gtk.Adjustment.new(0, 0, 1e8, 1, 10, 10)), "value"),
            (Adw.SwitchRow(title="Has Children", name="has_children"), "active"),)
editable[0][0].connect("tag-widget-added", tag_widget_added)
for i in ratings: rating_group.add(Adw.Toggle(label=i[:1], tooltip=i))
def sync_post(*_):
    if app.modifying: return
    app.modifying = True
    p = edit.p
    for l in (editable, dates):
        for i in l:
            w, prop = i if isinstance(i, Gtk.Calendar) else i[0], "date" if isinstance(i, Gtk.Calendar) else i[1]
            if not w.get_ancestor(Adw.PreferencesRow).get_mapped(): continue
            v = w.get_property(prop)
            names = w.get_name().split(" || ")
            for name in names:
                if name in sites[p.s]["overrides"] and callable(sites[p.s]["overrides"][name][1]):
                    v = sites[p.s]["overrides"][name][1](v)
            for name in names:
                if name in p.o:
                    p.o[name] = v.to_utc().to_unix() if isinstance(v, GLib.DateTime) else v
    app.data["Favorites"][p.s] = [p.o if i["id"] == p.o["id"] else i for i in app.data["Favorites"][p.s]]
    app.modifying = False
for i in dates: i.calendar.connect(f"notify::date", sync_post)
for i in editable: i[0].connect(f"notify::{i[1]}", sync_post)

info = tuple(Adw.ActionRow(title=i, subtitle_selectable=True, css_classes=("property",)) for i in ("ID", "Uploader", "Size", "Format", "Hash"))
for n, i in ((1, tuple(i[0] for i in editable[1:])), (1, dates), (2, info)):
    group = Adw.PreferencesGroup()
    for it in i:
        if isinstance(it, Adw.PreferencesRow):
            group.add(it)
        elif isinstance(it, Adw.ToggleGroup):
            (r := Adw.ActionRow(title=it.get_name().title()), r.add_suffix(it), group.add(r))
    pages[n].add(group)

group = Adw.PreferencesGroup(separate_rows=True)
ai_tag_button = Adw.ButtonRow(title="AI Autotag", css_classes=("button", "activatable", "suggested-action"), tooltip_text="Upload to Danbooru AI Tagger")
def ai_ai(b):
    form_data = Soup.Multipart.new("multipart/form-data")
    form_data.append_form_file("file", "image.png", "image/png", edit.p.get_child().get_paintable().get_current_image().save_to_png_bytes())
    form_data.append_form_string("format", "json")
    mes = Soup.Message.new_from_multipart("https://autotagger.donmai.us/evaluate", form_data)   
    b = app.session.send_and_read(mes)
    if mes.get_status() == 200:
        editable[0][0].tags = [i for i in json(b.get_data())[0]["tags"]]
        Toast(title=f"Done!", timeout=2)
    else: Toast(title=f"Server returned {mes.get_status()}!")
ai_tag_button.connect("activated", ai_ai)
group.add(ai_tag_button)
group.add(editable[0][0])
pages[0].add(group)

def show_edit(b, *_):
    if app.modifying: return
    app.modifying = True
    edit.p = p = b.get_ancestor(Gtk.Overlay)
    map_download()
    for i in info:
        if i.get_title() == "Format":
            i.set_subtitle(Gio.content_type_get_description(Gio.content_type_guess(get_property(p.o, "file_url", p.s))[0]))
        else:
            v = get_property(p.o, i.get_title().lower(), p.s)
            i.set_visible(bool(v))
            if v:
                i.set_subtitle(str(v))
    for i in dates:
        v = get_property(p.o, i.get_name(), p.s)
        i.set_visible(bool(v))
        if i.get_visible():
            i.calendar.set_date(GLib.DateTime.new_from_unix_utc(v) if isinstance(v, int) else v)
    for i in editable:
        v = get_property(p.o, i[0].get_name(), p.s)
        i[0].set_visible(v is not None)
        if v != None: i[0].set_property(i[1], v)
    edit.present(app.window)
    app.data["Favorites"][p.s] = [p.o if i["id"] == p.o["id"] else i for i in app.data["Favorites"][p.s]]
    app.modifying = False

def apply_colors(*_):
    v = None
    if view.get_selected_page().get_child().get_child():
        v = view.get_selected_page().get_child().get_child().get_child().get_child().get_child()
        v = v.get_paintable() if hasattr(v, "get_paintable") else None
    GLib.idle_add(set_colors, v, True)
    return False

for i in app.data["Tabs"]:
    t = Tab(q=i[0], p=i[1], s=i[2])
    view.set_page_pinned(t, i[3])
if not view.get_selected_page(): Tab()
getattr(preferences, "View Post Colors Theming").bind_property("active", Action("colors", apply_colors, stateful=False), "state", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, lambda b, v: GLib.Variant("b", v))
GLib.idle_add(tab_changed)
app.run()
