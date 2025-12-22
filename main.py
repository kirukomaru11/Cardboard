#!/usr/bin/python3
from json import loads as json
from html.parser import HTMLParser

from AppUtils import *

style = """
toggle-group toggle { padding: 0px 2px; }
row.expander .suffixes box { border-spacing: 4px; }
thread .heading { color: var(--red-3); font-weight: bold; }
.quote, .greentext { color: var(--green-4); }
.rquote { color: var(--red-2); font-style: italic; }
.url { text-decoration-style: unset; text-decoration-color: transparent; text-decoration: none; color: var(--blue-4); }
.spoiler { padding: 0px 4px; margin: 0px 2px; background: var(--dark-5); color: var(--dark-5); transition: color 0.3s; border-radius: 4px; }
.spoiler:hover { color: var(--light-1); }
.bold { font-weight: bold; }
.italic { font-style: italic; }
.code { font-family: monospace; }

thread { border-spacing: 10px; font-size: 20px; margin-bottom: 10px; }
reply header .url { font-size: 15px; }
reply { transition: background-color 0.3s; margin: 0px 10px; border-radius: 10px; padding: 10px; background: var(--shade-color); }
.highlight { background: color-mix(in srgb, var(--shade-color) 90%, var(--window-fg-color)); }
reply:first-child { background: none; margin: 0px;}
reply header > label:first-child { font-weight: bold; }
reply media { margin: 4px 0px; min-width: 120px; min-height: 50px; }
.thread-preview media,
.thread-preview picture { border-radius: 0px; }
.thread-preview {
  box-shadow: var(--card-shade-color) 0px 1px 5px 1px, var(--card-shade-color) 0px 2px 14px 3px;
  border-radius: 13px;
}
.thread-preview scrolledwindow label { font-size: 20px; }
.thread-preview viewport  { padding: 10px; }

media > image { color: white; }

tabview :not(masonrybox) .spinner { min-width: 200px; min-height: 400px; }
reply media > label,
tabview masonrybox media label { margin: 0px 0px 8px 8px; padding: 6px 10px 6px 10px; border-radius: 14px; font-weight: bold; }
reply media > revealer > box,
tabview masonrybox media box { border-spacing: 6px; }
media > revealer > box,
widget > media picture { margin: 6px; }
reply media > revealer > box > button,
masonrybox button { border-radius: 100px; }
reply media > revealer > box > button,
widget > media revealer > box,
masonrybox button,
media > label { background: rgba(0, 0, 0, 0.3); color: white; font-size: 15px; }
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

notes { font-weight: bold; margin-bottom: 8px; }
.notes { padding: 10px; }

sheet,
toolbarview {
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
.colored toolbarview {
  background: linear-gradient(to bottom right, color-mix(in srgb, var(--color-1) 45%, transparent), transparent),
    linear-gradient(to bottom left, color-mix(in srgb, var(--color-2) 45%, transparent), transparent),
    linear-gradient(to top, color-mix(in srgb, var(--color-3) 45%, transparent), transparent),
    var(--window-bg-color);
}
.colored controls.toolbar.card,
.colored widget > media revealer > box { background: color-mix(in srgb, var(--color-3), transparent 60%); }
"""
default_post = {"ID": lambda f: int(max((i["ID"] for i in f), default=0) + 1), "Hash": lambda: str(GLib.DateTime.new_now_utc().to_unix_usec()), "Rating": 0, "Source": "", "Has Children": False, "Parent ID": 0, "Tags": [], "Notes": "", "Added": lambda: GLib.DateTime.new_now_utc().to_unix(), "Created At": lambda: GLib.DateTime.new_now_utc().to_unix(), "File URL": "", "Preview URL": ""}
search_keys = dict((i.lower().replace(" ", "_"), i) for i in default_post.keys())
limit, ratings = 40, ("General", "Sensitive", "Questionable", "Explicit")

def shutdown(*_):
    try:
        app.shutdown = True
        app.data["Tabs"] = tuple((q[0], q[1], q[2], i.get_pinned()) for i in view.get_pages() for q in [i.history[i.index]])
        data_save()
    except:
        app.shutdown = False

app = App(shortcuts={"General": (("Add File", "app.add-file"), ("Add URL", "app.add-url"), ("Paste File/Image/URL", "<primary>v"), ("Keyboard Shortcuts", "app.shortcuts"), ("Preferences", "app.preferences"), ("Fullscreen", "app.fullscreen")), "Tabs": (("Overview", "app.overview"), ("Open in Browser", "app.open-current"), ("New Tab", "app.new-tab"), ("Close Tab", "app.close"), ("Reopen Closed Tab", "app.reopen-tab"), ("Toggle Favorite/Bookmark", "app.favorite"), ("Edit Post", "app.edit"), ("Download Post", "app.download"))},
          shutdown=shutdown,
          application_id="io.github.kirukomaru11.Cardboard",
          style=style,
          data={
            "Window": { "default-height": 600, "default-width": 600, "maximized": False },
            "General": { "New Tab Site": "Favorites", "New Tab Query": "", "Autocomplete": True, "Post Colors Theming": True },
            "Tags": { "Bookmarks": [], "Blacklist": [] },
            "Tabs": (),
            "Sites": {}
          })
app.data["Sites"].setdefault("Favorites", {})
app.modifying, app.sites, app.shutdown = False, {}, False

def get_property(o, k, s):
    site = app.sites[s]
    e = engines[site["Engine"].get_selected_item().get_string()]
    if k in e["overrides"]:
        f = e["overrides"][k][0] if isinstance(e["overrides"][k], tuple) else e["overrides"][k]
        if callable(f):
            if "url_dependant" in e and k in e["url_dependant"]: return f(o, site["URL"].get_text())
            else: return f(o)
        else: return f
    if k in o: return o[k]
    if k.lower().replace(" ", "_") in o: return o[k.lower().replace(" ", "_")]

def fetch_favorite_catalog(queries, site):
    catalog = []
    queries, s = " ".join(tuple(i for i in queries.split(" ") if not i.lower().startswith("order:"))).split(" + "), tuple(i for i in queries.split(" ") if i.lower().startswith("order:"))
    s = s[0].lower().split(":")[1] if s else "added"
    for query in queries:
        query += app.sites[site]["Append to Search"].get_text()
        terms = tuple(i for i in query.split(" ") if i and not i.startswith(("-site:", "site:")))
        key_terms = tuple(i for i in terms if ":" in i and len(i.split(":")) == 2)
        terms = tuple(i for i in terms if not i in key_terms)
        key_terms = tuple(i.split(":") for i in key_terms)
        key_terms = tuple([i[0].replace("regex_", ""), regex(i[1]) if i[0].startswith("regex_") else ratings.index(i[1].title()) if i[0] == "rating" and i[1].title() in ratings else i[1]] for i in key_terms)
        for key in key_terms:
            if key[0] in search_keys:
                key[0] = search_keys[key[0]]
        term_sites = [i.replace("_", " ") for i in query.split(" ") if i.startswith(("-site:", "site:"))]
        if not tuple(i for i in term_sites if i.startswith("site:")):
            term_sites += [i.get_string() for i in sites if not tuple(it for it in term_sites if it.split(":")[-1] == i.get_string())]
        term_sites = tuple(i.split(":")[-1] for i in term_sites if not i.startswith("-") and i.split(":")[-1] in app.data["Sites"])
        for site in term_sites:
            for p in app.data["Sites"][site]["Favorites"]:
                for k, v in key_terms:
                    if hasattr(v, "search"):
                        if not v.search(str(p[k])): break
                    else:
                        if not k in p or not v in str(p[k]): break
                else:
                    for term in terms:
                        if term.startswith("-"):
                            if term.lstrip("-") in p["Tags"]: break
                        if not (term in p["Tags"] or term in p["Notes"]): break
                    else: catalog.append((p, site))
    if "random" in s:
        k = random_sort
    else:
        k = lambda c: c[0][next((i for i in c[0] if i.lower().replace(" ", "_") == s.split("_asc")[0]), "Added")]
    catalog.sort(key=k, reverse=not "_asc" in s)
    return catalog

def fetch_online(site, queries, page, count=False):
    catalog = [0, []]
    en = app.sites[site]["Engine"].get_selected_item().get_string()
    e = engines[en]
    url, append = app.sites[site]["URL"].get_text(), app.sites[site]["Append to Search"].get_text()
    for query in queries.split(" + "):
        func = "fetch_thread" if "parent:" in query and "fetch_thread" in e else "fetch_post" if "id:" in query  and "fetch_post" in e else "fetch_catalog"
        u = e[func](query, page, url) if "url_dependant" in e and func in e["url_dependant"] else (url + e[func](query, page))
        response = json(app.session.send_and_read(Soup.Message.new("GET", u + append)).get_data().decode("utf-8"))
        c = e[func.replace("fetch", "get")](response) if func.replace("fetch", "get") in e else response
        if func == "fetch_catalog" and query and "filter_catalog" in e and e["filter_catalog"]:
            c = tuple(i for i in c if query in get_property(i, "comment", site))
        catalog[1] += c
        if count:
            if not "get_count" in e or func in ("fetch_thread", "fetch_post"):
                catalog[0] = len(catalog[1])
            else:
                n = response
                if "fetch_count" in e:
                    n = app.session.send_and_read(Soup.Message.new("GET", url + e["fetch_count"](query) + append)).get_data().decode("utf-8")
                if "get_count" in e:
                    catalog[0] += e["get_count"]((n, response))
                if isinstance(n, int):
                    catalog[0] += n
    if " + " in queries: catalog[1].sort(key=lambda i: get_property(i, "ID", site), reverse=True)
    return catalog

def format_post(p, site):
    new = {}
    for i in default_post: new.setdefault(i, get_property(p, i, site))
    for i in default_post:
        if callable(default_post[i]):
            if not isinstance(new[i], int):
                if i == "ID":
                    new[i] = default_post[i](app.data["Sites"][site]["Favorites"])
                elif i == "Hash":
                    if not isinstance(new[i], str):
                        new[i] = str(default_post[i]())
                else:
                    new[i] = default_post[i]()
        elif type(default_post[i]) != type(new[i]):
            new[i] = default_post[i]
    return new

def general_add(site, url):
    if "?" in url and "tags=" in url:
        tags = GLib.Uri.parse_params(url.split("?")[-1], -1, "&", GLib.UriParamsFlags.NONE)["tags"].replace(" + ", " ")
        if tags in getattr(preferences, "Bookmarks").tags: Toast(f"{tags} already in bookmarks!")
        else:
            getattr(preferences, "Bookmarks").tags += [tags]
        return Toast(f"{tags} added to bookmarks", timeout=2)
    en = app.sites[site]["Engine"].get_selected_item().get_string()
    p_id = False
    if en == "Danbooru":
        url = url.replace("/post/show/", "/posts/")
        if "/posts/" in url:
            p_id = url.split("?")[0].split("/posts/")[-1]
    if en == "Gelbooru" and "id=" in url:
        p_id = GLib.Uri.parse_params(url.split("?")[-1], -1, "&", GLib.UriParamsFlags.NONE)["id"]
    if en == "Moebooru" and "/post/show/" in url:
        p_id = url.split("?")[0].split("/post/show/")[-1].split("/")[0]
    if p_id:
        if tuple(i for i in app.data["Sites"][site]["Favorites"] if i["ID"] == int(p_id)): return Toast(f"{p_id} already in {site}'s favorites!", timeout=0)
        query = f"id:{p_id}"
    elif "thread/" in url or "res/" in url:
        p_id = url.split("res/" if en == "vichan" else "thread/")[1].split(".")[0].split("#")[0]
        post = url.split("p#" if en == "4chan" else "#")
        p_id = int(p_id.strip("/"))
        post = post[1].strip("q").strip("p") if len(post) > 1 else p_id
        query = f"parent:{p_id}"
    else: return Toast(f"URL: {url}\nCouldn't find the post")
    try:
        p = fetch_online(site, query, 0)[1]
        p = next((i for i in p if int(get_property(i, "ID", site)) == int(post)), None) if "fetch_thread" in engines[en] else p[0]
        p = format_post(p, site)
        app.data["Sites"][site]["Favorites"].append(p)
        return Toast(f"{p['ID']} added to {site}'s favorites", timeout=2)
    except Exception as e: return Toast(f"URL: {url}\nError: {e}")
match_embed = regex(r'src="(.*?)"').search
match_href = regex(r'href="(.*?)"').search
engines = {
"Cardboard": {
    "overrides": {},
},
"Danbooru": {
    "fetch_catalog": lambda t, p: f"/posts.json?limit={limit}&page={p}&tags={t}",
    "get_catalog": lambda c: tuple(i for i in c if "file_url" in i and not i["file_url"].endswith("swf")),
    "fetch_count": lambda t: f"/counts/posts.json?tags={t}",
    "get_count": lambda d: (c := json(d[0]), c["counts"]["posts"] if c["counts"]["posts"] else 0)[1],
    "get_url": lambda q: f"/posts/{q[0]['ID']}" if isinstance(q[0], dict) else f"/posts?page={q[1]}&tags={q[0]}",
    "overrides": {
        "Hash": lambda p: p["md5"],
        "Rating": lambda p: ratings.index(next(i for i in ratings if i.lower().startswith(p["rating"]))),
        "Tags": lambda p: [tag for i in ("artist", "copyright", "character", "general", "meta") for tag in p[f"tag_string_{i}"].split(" ") if tag],
        "Preview URL": lambda p: p["preview_file_url"].replace("180x180", "720x720").replace(".jpg" if "/180x180/" in p["preview_file_url"] else ".webp", ".webp"),
        "Parent ID": lambda p: 0 if p["parent_id"] is None else p["parent_id"],
        "File URL": lambda p: "" if not "file_url" in p else p["large_file_url"] if p["file_url"].endswith("zip") else p["file_url"],
        "Created At": lambda p: GLib.DateTime.new_from_iso8601(p["created_at"]).to_utc().to_unix(),
    }
},
"Gelbooru": {
    "fetch_catalog": lambda t, p: f"/index.php?limit={limit}&pid={p - 1}&page=dapi&s=post&q=index&json=1&tags={t}",
    "get_catalog": lambda c: c["post"] if "post" in c else [],
    "get_count": lambda c: c[1]["@attributes"]["count"],
    "get_url": lambda q: f"/index.php?page=post&s=view&id={q[0]['ID']}" if isinstance(q[0], dict) else f"/index.php?page=post&s=list&pid={q[1] - 1}&tags={q[0]}",
    "overrides": {
        "Hash": lambda p: p["md5"],
        "Tags": lambda p: p["tags"].split(" "),
        "Rating": lambda p: ratings.index(p["rating"].title()),
        "Has Children": lambda p: p["has_children"] == "true",
        "Created At": lambda p: (d := p["created_at"].rsplit(" ", 2), t := d.pop(1), da := Soup.date_time_new_from_http_string(" ".join(d)).format_iso8601().replace("Z", t), GLib.DateTime.new_from_iso8601(da).to_unix())[-1],
    }
},
"Moebooru": {
    "fetch_catalog": lambda t, p: f"/post.json?limit={limit}&page={p}&json=1&tags={t}",
    "fetch_count": lambda t: f"/post.xml?tags={t}",
    "get_count": lambda c: int(xml(c[0]).attrib["count"]),
    "get_url": lambda q: f"/post?id={q[0]['ID']}" if isinstance(q[0], dict) else f"/post?page={q[1]}&tags={q[0]}",
    "overrides": {
        "Hash": lambda p: p["md5"],
        "Tags": (lambda p: p["tags"].split(" "), lambda t: " ".join(t)),
        "Rating": lambda p: ratings.index(next(i for i in ratings if i.lower().startswith(p["rating"])))
        }
},
"FoolFuuka": {
    "fetch_catalog": lambda query, page, url: f"{url.rsplit('/', 2)[0]}/_/api/chan/gallery/?board={url.rsplit('/', 2)[1]}&page={page}",
    "fetch_thread": lambda query, page, url: f"{url.rsplit('/', 2)[0]}/_/api/chan/thread/?board={url.rsplit('/', 2)[1]}&num={query.split('parent:')[-1]}",
    "fetch_post": lambda query, page, url: f"{url.rsplit('/', 2)[0]}/_/api/chan/post/?board={url.rsplit('/', 2)[1]}&num={query.split('id:')[-1]}",
    "get_catalog": lambda c: sorted(c, key=lambda i: int(i["nreplies"]), reverse=True),
    "get_thread": lambda c: ([c[next(iter(c))]["op"]] + ([c[next(iter(c))]["posts"][i] for i in c[next(iter(c))]["posts"]] if "posts" in c[next(iter(c))] else [])) if len(c) == 1 else [],
    "get_post": lambda c: [c] if c["media"] else [],
    "get_url": lambda q: (s := q[0]["Parent ID"] if isinstance(q[0], dict) else q[0].split(":")[1] if "parent:" in q[0] else False, f"thread/{s}" if s else "")[-1],
    "filter_catalog": True,
    "url_dependant": ("fetch_catalog", "fetch_thread", "fetch_post", "Source"),
    "overrides": {
        "replies": lambda o: o["nreplies"] if o["nreplies"] is None else int(o["nreplies"]),
        "filename": lambda o: o["media"]["media_orig"],
        "comment": lambda o: (f"<b>{o['title']}</b><br>" if "title" in o and o["title"] else "") + o["comment_processed"],
        "country": lambda o: o["poster_country"],
        "country_name": lambda o: o["poster_country_name"],
        "poster_id": lambda o: o["poster_hash"],
        "Tags": lambda o: [o["media"]["media_filename"], o["media"]["media_orig"]],
        "Source": lambda o, url: f"{url}thread/{o['thread_num']}",
        "ID": lambda o: int(o["num"]),
        "Hash": lambda o: o["media"]["media_hash"],
        "File URL": lambda o: o["media"]["media_link"],
        "Preview URL": lambda o: o["media"]["thumb_link"],
        "Created At": lambda o: o["timestamp"],
        "Parent ID": lambda o: int(o["thread_num"]) if o["thread_num"] != o["num"] else 0,
        "Has Children": lambda o: o["op"] == "1"
        ,},
},
"vichan": {
    "fetch_catalog": lambda *_: "catalog.json",
    "fetch_thread": lambda query, page: f"res/{query.split('parent:')[-1]}.json",
    "get_catalog": lambda c: tuple(t for i in c for t in i["threads"]),
    "get_thread": lambda c: c["posts"],
    "get_url": lambda q: (s := q[0]["ID"] if isinstance(q[0], dict) else q[0].split(":")[1] if "parent:" in q[0] else False, f"res/{s}.html" if s else "")[-1],
    "filter_catalog": True,
    "url_dependant": ("Source", "File URL", "Preview URL"),
    "overrides": {
        "filename": lambda o: (o["filename"] + o["ext"]) if "filename" in o else "",
        "comment": lambda o: (f"<b>{o['sub']}</b><br>" if "sub" in o else "") + (o["com"] if "com" in o else ""),
        "poster_id": lambda o: o["id"],
        "Tags": lambda o: [o["filename"] + o["ext"], str(o["tim"]) + o["ext"]] if "filename" in o else [],
        "Source": lambda o, url: f"{url}thread/{o['no'] if o['resto'] == 0 else o['resto']}",
        "ID": lambda o: int(o["no"]),
        "Hash": lambda o: o["md5"] if "md5" in o else str(o["no"]),
        "File URL": lambda o, url: ("https://" + match_embed(o["embed"]).group(1).strip("https:").strip("//")) if "embed" in o and "src" in o["embed"] else f"{url}src/{o['tim']}{o['ext']}",
        "Preview URL": lambda o, url: f"{url}static/deleted.png" if "filedeleted" in o and o["filedeleted"] == 1 else f"{url}static/spoiler.png" if "spoiler" in o and o["spoiler"] == 1 else ("https://" + match_embed(o["embed"]).group(1).strip("https:").strip("//")) if "embed" in o and "src" in o["embed"] else f"{url}thumb/{o['tim']}{'.jpg' if Gio.content_type_guess(o['ext'])[0].startswith('video') else o['ext']}",
        "Created At": lambda p: GLib.DateTime.new_from_unix_local(p["time"]).to_utc().to_unix(),
        "Parent ID": lambda o: o["resto"],
        "Has Children": lambda o: o["resto"] == 0
        ,},
},
"4chan": {
    "fetch_catalog": lambda *_: "catalog.json",
    "fetch_thread": lambda query, page: f"thread/{query.split('parent:')[-1]}.json",
    "get_catalog": lambda c: [thread for i in c for thread in i["threads"]],
    "get_thread": lambda c: c["posts"],
    "get_url": lambda q: (s := q[0]["Parent ID"] if isinstance(q[0], dict) else q[0].split(":")[1] if "parent:" in q[0] else False, f"thread/{s}" if s else "")[-1],
    "filter_catalog": True,
    "url_dependant": ("Source", "File URL", "Preview URL"),
    "overrides": {
        "filename": lambda o: o["filename"] + o["ext"],
        "comment": lambda o: (f"<b>{o['sub']}</b><br>" if "sub" in o else "") + (o["com"] if "com" in o else ""),
        "poster_id": lambda o: o["id"] if "id" in o else None,
        "Tags": lambda o: [o["filename"] + o["ext"], str(o["tim"]) + o["ext"]] if "filename" in o else [],
        "Source": lambda o, url: f"{url}thread/{o['no'] if o['resto'] == 0 else o['resto']}",
        "ID": lambda o: int(o["no"]),
        "Hash": lambda o: o["md5"] if "md5" in o else str(o["no"]),
        "File URL": lambda o, url: f"https://i.4cdn.org/{url.rsplit('/', 2)[1]}/{o['tim']}{o['ext']}" if "tim" in o else "",
        "Preview URL": lambda o, url: f"https://i.4cdn.org/{url.rsplit('/', 2)[1]}/{o['tim']}s.jpg" if "tim" in o else "",
        "Created At": lambda o: o["time"],
        "Parent ID": lambda o: o["resto"],
        "Has Children": lambda o: o["resto"] == 0
        ,},
},
"jschan": {
    "fetch_catalog": lambda *_: "catalog.json",
    "fetch_thread": lambda query, page: f"thread/{query.split('parent:')[-1]}.json",
    "get_url": lambda q: (s := q[0]["ID"] if isinstance(q[0], dict) else q[0].split(":")[1] if "parent:" in q[0] else False, f"thread/{s}.html" if s else "")[-1],
    "get_thread": lambda c: ([c] + c["replies"]) if "replies" in c else [c],
    "filter_catalog": True,
    "url_dependant": ("Source", "File URL", "Preview URL"),
    "overrides": {
        "replies": lambda o: o["replyposts"] if "replyposts" in o else None,
        "filename": lambda o: o["files"][0]["originalFilename"],
        "comment": lambda o: ((f"<b>{o['subject']}</b><br>" if o["subject"] != None else "") + (o["message"] if o["message"] != None else "")).replace("\n", "<br>"),
        "poster_id": lambda o: o["userId"],
        "country": lambda o: o["country"]["code"] if o["country"] else None,
        "country_name": lambda o: o["country"]["name"] if o["country"] else None,
        "Tags": lambda o: [o["filename"] + o["ext"], str(o["tim"]) + o["ext"]] if "filename" in o else [],
        "Source": lambda o, url: f"{url}thread/{o['postId'] if o['thread'] == None else o['thread']}.html",
        "ID": lambda o: o["postId"],
        "Hash": lambda o: o["files"][0]["hash"],
        "File URL": lambda o, url: f"{url.rsplit('/', 2)[0]}/file/{o['files'][0]['filename']}",
        "Preview URL": lambda o, url: f"{url.rsplit('/', 2)[0]}/file/thumb/{o['files'][0]['hash']}{o['files'][0]['thumbextension']}" if o["files"][0]["hasThumb"] else "",
        "Created At": lambda o: GLib.DateTime.new_from_iso8601(o["date"]).to_utc().to_unix(),
        "Parent ID": lambda o: o["thread"] if o["thread"] else 0,
        "Has Children": lambda o: o["thread"] == None
        ,},
},
}

fail_url = lambda u, e=None: Toast(f"{u}\nError: {e}" if e else f"\n{u} could not be added!")
def add_favorite(p):
    if not site_row.get_selected_item(): add_site("Favorites")
    s = site_row.get_selected_item().get_string() if app.sites[site_row.get_selected_item().get_string()]["Engine"].get_selected_item().get_string() == "Cardboard" else tuple(i for i in app.sites if app.sites[i]["Engine"].get_selected_item().get_string() == "Cardboard")[0]
    p = format_post(p, s)
    for i in ("File URL", "Preview URL"):
        if p[i] and not p[i].startswith("http"):
            p[i] = f"file://{p[i]}"
    app.data["Sites"][s]["Favorites"].append(p)
    Toast(f"Post {p['ID']} added to favorites!", timeout=2)
def add_from_url(s, r, fun, url):
    b = s.send_and_read_finish(r)
    if not b: fail_url(url)
    try: fun(b, url)
    except Exception as e: fail_url(url, e)
def zerochan_add(b, url):
    p = json(b.get_data().decode("utf-8"))
    add_favorite({"File URL": p["full"], "Preview URL": p["medium"], "Source": p["source"], "Hash": p["hash"], "Tags": p["tags"]})
def twitter_add(b, url):
    medias = []
    if "/status/" in url:
        h = xml(b.get_data().decode("utf-8"))
        for i in h.findall(".//div[@id='m'][@class='main-tweet']//a[@class='still-image']"): medias.append(i.attrib["href"].split("%2F")[1])
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
        add_favorite({"File URL": file_url, "Source": url.replace("nitter.net", "x.com") if "/status/" in url else file_url, "Preview URL": file_url.replace("orig", "small")})
def artstation_add(b, url):
    res = json(b.get_data().decode("utf-8"))
    created_at = GLib.DateTime.new_from_iso8601(res["created_at"]).to_utc().to_unix()
    tags = res["tags"] + res["title"].split(" ") + res["user"]["username"].split(" ")
    for i in res["assets"]:
        file_url = i["image_url"]
        for it in ("/small/", "/large/", "/medium/"):
            file_url = file_url.replace(it, "/4k/")
        add_favorite({"File URL": file_url, "Source": url, "Preview URL": file_url.replace("/4k/", "/small/"), "Created At": created_at, "Tags": tags})
def reddit_add(b, url):
    res, to_add = b.get_data().decode("utf-8"), []
    if "<gallery-carousel style=" in res:
        for i in res.split("<gallery-carousel style=")[1].split('src="'):
            if i.startswith("https://preview.redd.it/"):
                i = f"https://i.redd.it/{i.split('?')[0].rsplit('-', 1)[1   ]}"
                if not i in to_add: to_add.append(i)
    else: to_add.append(res.rsplit("i18n-post-media-img", 1)[1].split('src="')[1].split('"')[0])
    for i in to_add: add_favorite({"File URL": i, "Source": url, "Preview URL": i})
def pinterest_add(b, url):
    file_url = b.get_data().decode("utf-8").split('"ImageDetails","url":"')[1].split('"')[0]
    add_favorite({"File URL": file_url, "Source": url, "Preview URL": file_url.replace("originals", "1200x"), "Hash": file_url.split("/")[-1].split(".")[0]})
def kemono_add(b, url):
    post = json(b.get_data().decode("utf-8"))
    created_at = GLib.DateTime.new_from_iso8601(post["post"]["published"], GLib.TimeZone.new_utc()).to_unix()
    for i in post["previews"]:
        if Gio.content_type_guess(i["name"])[0].startswith(("video", "image")): add_favorite({"File URL": f'{i["server"]}/data{i["path"]}', "Hash": i["path"].split("/")[-1].split(".")[0], "Source": url, "Preview URL":f'https://img.kemono.cr/thumbnail/data{i["path"]}', "Created At": created_at})

extra = {"Zerochan": (lambda u: u.startswith("https://www.zerochan.net/") and u.split("/")[-1].isdigit(), lambda u: app.session.send_and_read_async(Soup.Message.new("GET", f"{u}?&json"), GLib.PRIORITY_DEFAULT, None, add_from_url, *(zerochan_add, u))),
        "Twitter": (lambda u: u.replace("https://", "").startswith(("xcancel.com", "twitter.com", "x.com", "nitter.net", "cdn.xcancel.com", "pbs.twimg.com")), lambda u: (url := u.replace("x.com", "nitter.net").replace("xcancel.com", "nitter.net").replace("twitter.com", "nitter.net"), app.session.send_and_read_async((m := Soup.Message.new("GET", url), tuple(m.get_request_headers().append(k, v) for k, v in (("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"), ("Accept-Language", "en-US,en;q=0.5"), ("Sec-Fetch-Dest", "document"))), m)[-1], GLib.PRIORITY_DEFAULT, None, add_from_url, *(twitter_add, url)))),
        "Artstation": (lambda u: "artstation.com/artwork/" in u, lambda u: app.session.send_and_read_async(Soup.Message.new("GET", f"{u.replace('artwork', 'projects')}.json"), GLib.PRIORITY_DEFAULT, None, add_from_url, *(artstation_add, u))),
        "Reddit": (lambda u: u.startswith("https://www.reddit.com/r/") and "/comments/" in u, lambda u: app.session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, add_from_url, *(reddit_add, u))),
        "Pinterest": (lambda u: "pinterest.com/pin/" in u, lambda u: app.session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, add_from_url, *(pinterest_add, u))),
        "Kemono": (lambda u: u.startswith("https://kemono.cr") and "user" in u and "post" in u, lambda u: app.session.send_and_read_async((m := Soup.Message.new("GET", u.replace(".cr", ".cr/api/v1/")), m.get_request_headers().append("Accept", "text/css"), m)[-1], GLib.PRIORITY_DEFAULT, None, add_from_url, *(kemono_add, u))),
        "YouTube": (lambda u: ("youtu.be/" in u or "youtube.com" in u), lambda u: add_favorite({"Source": u.replace("www.", "").replace("be.com/watch?v=", ".be/").split("?")[0], "File URL": u.replace("www.", "").replace("be.com/watch?v=", ".be/").split("?")[0].replace("youtu.be", "img.youtube.com/vi/") + "/maxresdefault.jpg", "Preview URL": u.replace("www.", "").replace("be.com/watch?v=", ".be/").split("?")[0].replace("youtu.be", "img.youtube.com/vi") + "/mqdefault.jpg"})),
        }
def add(v, _hash=False):
    if isinstance(v, str):
        for url in v.split("\n"):
            url = url.strip()
            u = False
            for k in app.sites:
                su = app.sites[k]["URL"].get_text()
                if su and url.startswith(su):
                    app.thread.submit(general_add, k, url)
                    u = True
                    break
            for k in extra:
                if extra[k][0](url):
                    extra[k][1](url)
                    u = True
                    break
            if u: continue
            add_favorite({"File URL": url})
    if isinstance(v, Gdk.Texture):
        _hash = GLib.DateTime.new_now_utc().to_unix_usec()
        f = app.data_folder.get_child(f"{_hash}.png")
        v.save_to_png(f.peek_path())
        return add(Gdk.FileList.new_from_list((f,)), _hash)
    if isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            _hash = _hash or GLib.DateTime.new_now_utc().to_unix_usec()
            mimetype = Gio.content_type_guess(file.get_basename())[0]
            if not (mimetype.startswith(("video", "image")) or mimetype.endswith("zip")):
                fail_url(file.peek_path())
                continue
            f = app.data_folder.get_child(f"{_hash}.{file.peek_path().split('.')[-1]}")
            if not mimetype.endswith("zip"):
                pr = app.data_folder.get_child(f"preview-{_hash}.webp")
                generate_thumbnail(file, pr)
            if not f.equal(file): file.copy(f, Gio.FileCopyFlags.NONE)
            add_favorite({"Hash": str(_hash), "Source": file.get_uri(), "File URL": f.get_basename(), "Preview URL": "" if mimetype.endswith("zip") else pr.get_basename()})
file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "application/vnd.comicbook+zip", "video/*")), ("Image", ("image/*",)), ("Comic Book Archive", ("application/vnd.comicbook+zip",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))
Action("add-file", lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.window, None, lambda d, r: add(d.open_multiple_finish(r))), "<primary><shift>a")
add_url = EntryDialog(heading="Add URL to Bookmarks/Favorites", callback=lambda d: add(d.get_extra_child().get_buffer().get_property("text")), multiline=True)
Action("add-url", lambda *_: add_url.present(app.window), "<primary><shift>d")

def tag_widget_added(r, tag):
    for n in range(3):
        e = Gtk.GestureClick(button=n + 1)
        e.connect("pressed", tag_clicked)
        tag.get_first_child().add_controller(e)
engines_model = Gtk.StringList.new(tuple(engines))
Action("new-site", lambda *_: add_site(unique_name("New Site", app.data["Sites"])))
def do_delete_site(*_):
    sites.remove(sites.find(delete_site.r.get_title()))
    sites_group.remove(delete_site.r)
    del app.data["Sites"][delete_site.r.get_title()]
    for i in tuple(app.persist):
        if hasattr(i, "page") and i.page == "Sites" and i.group == delete_site.r.get_title(): app.persist.remove(i)
def rename_site(*_):
    name = unique_name(site_rename.get_extra_child().get_text(), app.data["Sites"])
    n = sites.find(site_rename.r.get_title())
    sites.splice(n, 1, (name, ))
    app.data["Sites"][name] = app.data["Sites"].pop(site_rename.r.get_title())
    app.sites[name] = app.sites.pop(site_rename.r.get_title())
    for i in app.persist:
        if hasattr(i, "page") and i.page == "Sites" and i.group == site_rename.r.get_title(): setattr(i, "group", name)
    site_rename.r.set_title(name)
site_rename = EntryDialog(callback=rename_site)
delete_site = Adw.AlertDialog(default_response="cancel")
delete_site.connect("response", lambda d, r: (d.close(), do_delete_site() if r == "confirm" else None))
for i in ("cancel", "confirm"): delete_site.add_response(i, i.title())
delete_site.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
site_defaults = {"URL": "", "Append to Search": "", "Launch Sources": False, "Download Favorites": False, "Engine": "Cardboard", "Favorites": []}
def move_site(d, v, x, y):
    if not d.get_widget().highlight: return False
    d.get_widget().highlight.remove_css_class("highlight")
    if not isinstance(d.get_widget().highlight, Adw.ExpanderRow): return False
    row, n_row = v, d.get_widget().highlight
    listbox = row.get_parent()
    if not n_row or row == n_row: return
    rows = tuple(i for i in listbox)
    n1, n2 = rows.index(n_row), rows.index(row)
    for n, i in ((n1, row), (n2, n_row)):
        sites.splice(n, 1, (i.get_title(),))
        listbox.remove(i)
        listbox.insert(i, n)
    rows = tuple(i.get_title() for i in listbox)
    app.data["Sites"] = dict(sorted(app.data["Sites"].items(), key=lambda i: rows.index(i[0])))
    return True
def d_prepare(e, x, y):
    child = e.get_widget().get_row_at_y(y)
    if not child: return None
    e.get_widget().row = child
    return Gdk.ContentProvider.new_for_value(child)
def highlight(e, x, y):
    if hasattr(e.get_widget(), "highlight") and e.get_widget().highlight: e.get_widget().highlight.remove_css_class("highlight")
    e.get_widget().highlight = e.get_widget().get_row_at_y(y)
    if e.get_widget().highlight:
        e.get_widget().highlight.add_css_class("highlight")
        return Gdk.DragAction.MOVE
    return Gdk.DragAction.NONE
def add_site(name):
    app.data["Sites"].setdefault(name, {})
    app.sites.setdefault(name, {})
    row, box = Adw.ExpanderRow(title=name), Gtk.Box(valign=Gtk.Align.CENTER)
    row.add_suffix(box)
    for c, i, t in ((lambda b: (setattr(site_rename, "r", b.get_ancestor(Adw.ExpanderRow)), site_rename.set_heading(f'Rename site "{site_rename.r.get_title()}"'), site_rename.present(app.window)), "document-edit", "Rename"), (lambda b: (setattr(delete_site, "r", b.get_ancestor(Adw.ExpanderRow)), delete_site.set_heading(f'Delete site "{delete_site.r.get_title()}"'), delete_site.present(app.window)), "user-trash", "Delete")): box.append(Button(callback=c, icon_name=i, tooltip_text=t, css_classes=("flat",)))
    box.get_last_child().add_css_class("destructive-action")
    for k, v in site_defaults.items():
        app.data["Sites"][name].setdefault(k, v)
        if isinstance(v, list): continue
        p = "active" if type(v) == bool else "text" if v == "" else "selected-item"
        app.persist.append(Adw.EntryRow() if p == "text" else Adw.SwitchRow() if p == "active" else Adw.ComboRow(model=engines_model))
        app.persist[-1].set_title(k)
        app.persist[-1].set_property("selected" if p == "selected-item" else p, app.persist[-1].get_model().find(app.data["Sites"][name][k]) if p == "selected-item" else app.data["Sites"][name][k])
        app.persist[-1].page, app.persist[-1].group, app.persist[-1].property = "Sites", name, p
        row.add_row(app.persist[-1])
        app.sites[name][app.persist[-1].get_title()] = app.persist[-1]
    sites_group.add(row)
    if sites.find(name) == GLib.MAXUINT32: sites.append(name)
sites = Gtk.StringList.new()
for i in app.data["Sites"]: sites.append(i)
preferences = Adw.PreferencesDialog(search_enabled=True, content_width=450, content_height=450)
Action("preferences", lambda *_: preferences.present(app.window), "<primary>p")
for p in app.data:
    if p in ("Window", "Favorites", "Tabs"): continue
    page = Adw.PreferencesPage(title=p, icon_name="preferences-system-symbolic" if p == "General" else "tag-outline-symbolic" if p == "Tags" else "folder-globe-symbolic" if p == "Sites" else "")
    if p == "Sites":
        sites_page = page
        sites_group = Adw.PreferencesGroup(separate_rows=True)
        sites_group.add(Adw.ButtonRow(action_name="app.new-site", title="Add Site", start_icon_name="list-add-symbolic"))
        listbox = sites_group.get_row(0).get_parent()
        drag = listbox.drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", d_prepare)
        drag.connect("drag-begin", lambda e, d: Gtk.DragIcon.get_for_drag(d).set_child(Gtk.Label(margin_top=10, margin_start=10, label=e.get_widget().row.get_title(), css_classes=("title-4",))))
        listbox.add_controller(drag)
        d = Gtk.DropTarget(preload=True, actions=Gdk.DragAction.MOVE, formats=Gdk.ContentFormats.parse("AdwExpanderRow"))
        d.connect("drop", move_site)
        d.connect("motion", highlight)
        listbox.add_controller(d)
        sites_page.add(sites_group)
        for i in app.data[p]: add_site(i)
    else:
        if p == "Tags":
            group = Adw.PreferencesGroup(separate_rows=True)
            for g in app.data[p]:
                app.persist.append(TagRow(title=g))
                app.persist[-1].connect("tag-widget-added", tag_widget_added)
                app.persist[-1].tags, app.persist[-1].property, app.persist[-1].path = app.data[p][g], "tags", p
                group.add(app.persist[-1])
                setattr(preferences, g, app.persist[-1])
            page.add(group)
        else:
            group = Adw.PreferencesGroup()
            for n, v in app.data[p].items():
                app.persist.append(Adw.ComboRow(model=sites, selected=sites.find(v)) if n == "New Tab Site" else Adw.SwitchRow(active=v) if type(v) is bool else Adw.EntryRow(text=v))
                app.persist[-1].set_title(n)
                app.persist[-1].path, app.persist[-1].property = p, "active" if isinstance(app.persist[-1], Adw.SwitchRow) else "text" if isinstance(app.persist[-1], Adw.EntryRow) else "selected-item"
                group.add(app.persist[-1])
                setattr(preferences, n, app.persist[-1])
            page.add(group)
    preferences.add(page)

search_popover = Gtk.Popover(child=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=("boxed-list",)))
site_row, page_row = Adw.ComboRow(title="Site", model=sites), Adw.SpinRow.new_with_range(1, 1000, 1)
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
    if app.modifying or not search.get_text() or not getattr(preferences, "Autocomplete").get_active(): return
    app.modifying = True
    m = Soup.Message.new("GET", f"https://danbooru.donmai.us/autocomplete.json?search[query]={search_current_word()}&search[type]=tag_query&limit=15")
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
    if tuple(i for i in app.data["Sites"][p.s]["Favorites"] if i["ID"] == p.o["ID"]): p.favorite.set_properties(tooltip_text="Remove Favorite", icon_name="starred-symbolic")
    else: p.favorite.set_properties(tooltip_text="Add Favorite", icon_name="star-new-symbolic")
    p_id, has_c = p.o["Parent ID"], p.o["Has Children"]
    tt = "Has Parent" if p_id else "Has Children"
    i = "folder-user" if p_id else "preferences-system-parental-controls"
    if p_id and has_c:
        tt, i = "Has Parent and Children", "system-users"
    p.related.set_properties(tooltip_text=tt, icon_name=f"{i}-symbolic", visible=int(p_id) > 0 or has_c)
def post_related(b):
    p = b.get_ancestor(Gtk.Overlay)
    p_id, has_c = p.o["Parent ID"], p.o["Has Children"]
    if p_id: Tab(q=f"parent:{p_id}", s=p.s)
    if has_c: Tab(q=f"parent:{p.o['ID']}", s=p.s)
def post_favorite(b):
    p = b.get_ancestor(Gtk.Overlay)
    if tuple(i for i in app.data["Sites"][p.s]["Favorites"] if i["ID"] == p.o["ID"]):
        app.data["Sites"][p.s]["Favorites"] = [i for i in app.data["Sites"][p.s]["Favorites"] if i["ID"] != p.o["ID"]]
    else:
        app.data["Sites"][p.s]["Favorites"].append(p.o)
        if app.sites[s]["Download Favorites"].get_active(): post_download(p)
    show_revealer(p.event)
def finish_func(picture, paintable):
    if not isinstance(picture.get_parent(), Gtk.Overlay):
        paintable.colors = palette(paintable, distance=160, black_white=300)
        GLib.idle_add(apply_colors)
    if hasattr(picture.get_parent(), "t") and picture.get_parent().t: picture.set_can_shrink(False)
app.finish_func = finish_func
Action("edit", lambda *_: view.get_selected_page().get_child().get_child().edit.emit("clicked") if hasattr(view.get_selected_page().get_child().get_child(), "edit") else None, "<primary>e")
def thumbnail_clicked(event, n_press, x, y):
    p = event.get_widget()
    if p.url: return(launch(p.url))
    p.loaded = not p.loaded if hasattr(p, "loaded") else True
    for i in p:
        if isinstance(i, Gtk.Image): i.set_visible(not p.loaded)
    if not event.get_widget().o["Preview URL"].endswith(".gif") and isinstance(p.get_child().controls, Gtk.MediaControls): p.get_child().controls.set_visible(p.loaded)
    app.thread.submit(load_media, p, p.o["File URL" if p.loaded else "Preview URL"])
def Post(o, s, p=False, t=False):
    e = app.sites[s]["Engine"].get_selected_item().get_string()
    e_url = None
    if "Hash" in o and "ID" in o and "Added" in o and "Notes" in o:
        comment, replies = False, None
    else:
        comment, replies = tuple(get_property(o, i, s) for i in ("comment", "replies"))
        o = format_post(o, s)
    file_url, preview_url = o["File URL"], o["Preview URL"]
    uri = file_url if (not p and file_url or not preview_url) else preview_url
    file, preview_file = tuple(app.data_folder.get_child(i) for i in (f"{o['Hash']}.{file_url.rsplit('.')[-1]}", f"preview-{o['Hash']}.{preview_url.rsplit('.')[-1]}"))
    fe, pe = tuple(os.path.exists(i.peek_path()) if i else False for i in (file, preview_file))
    uri = preview_file if pe and (p or not fe) else file if fe else uri
    if uri == "":
        uri = None
    post = Media(uri, overlay=True, controls=True if t else not p, play=True if t or p and ".gif" in (preview_url or file_url) else not p, scrollable=not p)
    buttons = tuple(Button(name=n, callback=c) for n, c in (("related", post_related), ("favorite", post_favorite), ("edit", show_edit)))
    for i in buttons: setattr(post, i.get_name(), i)
    post.edit.set_properties(icon_name="document-edit-symbolic", tooltip_text="Edit")
    revealer = Gtk.Revealer(child=Gtk.Box(), halign=Gtk.Align.END, valign=Gtk.Align.START, transition_type=Gtk.RevealerTransitionType.CROSSFADE)
    post.event.bind_property("contains-pointer", revealer, "reveal-child", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, toggle_revealer)
    post.add_overlay(revealer)
    if p:
        if Gio.content_type_guess(file_url)[0].startswith("video"): post.add_overlay(Gtk.Image(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER, pixel_size=50, icon_name="media-playback-start-symbolic"))
        if o["File URL"].startswith(("file://", "https://", "http://")):
            v = Gdk.FileList.new_from_list((file,)) if fe and o["File URL"].startswith("file://") else o["File URL"]
            drag_source = Gtk.DragSource(actions=Gdk.DragAction.COPY, content=Gdk.ContentProvider.new_for_value(v))
            drag_source.connect("drag-begin", lambda e, d: Gtk.DragIcon.get_for_drag(d).set_child(Adw.Clamp(maximum_size=250, orientation=Gtk.Orientation.VERTICAL, child=Adw.Clamp(maximum_size=250, child=Gtk.Picture(css_classes=("card",), paintable=e.get_widget().get_child().get_paintable())))))
            GLib.idle_add(post.add_controller, drag_source)
    else:
        post.get_child().get_child().set_properties(overflow=False, valign=Gtk.Align.CENTER)
        revealer.get_child().add_css_class("linked")
    for i in buttons: GLib.idle_add(revealer.get_child().append, i)
    post.file, post.preview_file = file, preview_file
    post.p, post.o, post.s, post.t = p, o, s, t
    post.event.connect("enter", show_revealer)
    if uri and not (fe and pe) and app.sites[s]["Download Favorites"].get_active() and o in app.data["Sites"][s]["Favorites"]: post_download(post)
    if t:
        for n, i in ((1, thumbnail_clicked), (2, lambda e, *_: Tab(q=e.get_widget().o, s=e.get_widget().s))):
            click = Gtk.GestureClick(button=n)
            click.connect("released", i)
            post.add_controller(click)
        post.url = e_url
        if e_url: post.set_tooltip_text(e_url)
    elif p and comment:
        box = Gtk.Box(overflow=Gtk.Overflow.HIDDEN, orientation=Gtk.Orientation.VERTICAL)
        intro = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, max_content_height=200, propagate_natural_height=True, child=Gtk.Viewport(valign=Gtk.Align.CENTER, child=Gtk.Box(halign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL)))
        ParseComment(comment, intro.get_child().get_child(), {"hexpand": True, "halign": Gtk.Align.CENTER, "justify": Gtk.Justification.CENTER,}, {"hexpand": True, "halign": Gtk.Align.CENTER})
        for i in (post, intro): box.append(i)
        post = box
        post.add_css_class("thread-preview")
    if isinstance(replies, int): post.set_tooltip_text(f"{replies} replies")
    return post
def open_link(label, uri):
    if uri.startswith(">>"):
        thread = label.get_ancestor(Gtk.Box).get_ancestor(Gtk.Box).get_parent()
        for i in thread:
            if i.get_name() == uri.strip(">>") and not "highlight" in i.get_css_classes():
                thread.get_parent().scroll_to(i)
                i.add_css_class("highlight")
            else: i.remove_css_class("highlight")
    else: launch(uri)
    return True
class ParseComment(HTMLParser):
    def __init__(self, comment, body, args={}, wargs={}):
        self.body, self.wrap, self.css, self.args, self.wargs = body, None, [], args, wargs
        super().__init__()
        self.body.append(Adw.WrapBox(**self.wargs))
        self.wrap = self.body.get_last_child()
        if comment: self.feed(comment)
    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.body.append(Adw.WrapBox(**self.wargs))
            self.wrap = self.body.get_last_child()
        if tag == "s": self.css.append("spoiler")
        if tag in ("b", "strong"): self.css.append("bold")
        if tag == "em": self.css.append("italic")
        if tag == "code": self.css.append("code")
        if tag == "a": self.css.append("url")
        if [i for i in attrs if i[0] == "class"]:
            self.css += [i[1] for i in attrs if i[0] == "class"][0].split(" ")
    def handle_data(self, data):
        args = { "selectable": True, "wrap": True, "wrap_mode": Pango.WrapMode.WORD_CHAR, "label": data.strip(), "css_classes": self.css }
        if "url" in self.css:
            args["label"] = GLib.markup_escape_text(args["label"])
            args["label"] = f'<a href="{args["label"]}" class="url">{args["label"]}</a>'
            args["use_markup"] = True
        label = Gtk.Label(**args, **self.args)
        if "url" in self.css: label.connect("activate-link", open_link)
        self.wrap.append(label)
    def handle_endtag(self, tag):
        self.css = []
def Reply(o, s, full):
    name, time, number, country, country_name, _id, tripcode, comment = tuple(get_property(o, i, s) for i in ("name", "Created At", "ID", "country", "country_name", "poster_id", "trip", "comment"))
    header, reply = Adw.WrapBox(css_name="header", child_spacing=8, line_spacing=2, halign=Gtk.Align.START), Gtk.Box(name=str(number), css_name="reply", halign=Gtk.Align.START, orientation=Gtk.Orientation.VERTICAL)
    for i in (name, GLib.DateTime.new_from_unix_utc(time).to_local().format("%x (%a) %T"), f"No.{number}"): header.append(Gtk.Label(selectable=True, halign=Gtk.Align.START, ellipsize=Pango.EllipsizeMode.END, label=i))
    if country: header.insert_child_after(Gtk.Label(selectable=True, halign=Gtk.Align.START, ellipsize=Pango.EllipsizeMode.END, label=country, tooltip_text=country_name), header.get_first_child())
    if _id: header.get_first_child().set_tooltip_text(_id)
    reply.append(header)
    medias = []
    if "media" in o and o["media"] or "filename" in o or "embed" in o: medias.append(o)
    if "extra_files" in o or "files" in o:
        for i in o["files" if "files" in o else "extra_files"]:
            no = dict(o)
            if "extra_files" in o:
                no.update(i)
            else:
                no["files"] = [i]
            medias.append(no)
    if len(medias) > 1:
        bottom = Adw.WrapBox(child_spacing=10, line_spacing=10)
        reply.append(bottom)
    else:
        bottom = reply
    for i in medias:
        filename = get_property(i, "filename", s)
        p = Post(i, s, True, True)
        p.set_properties(tooltip_text=filename, halign=Gtk.Align.START, valign=Gtk.Align.START)
        bottom.append(p)
    if comment: ParseComment(comment, reply, {"halign": Gtk.Align.START})
    for i in full:
        _comment = get_property(i, "comment", s)
        if not _comment: continue
        if f"&gt;&gt;{number}" in _comment:
            l = f"&gt;&gt;{get_property(i, 'ID', s)}"
            header.append(Gtk.Label(selectable=True, css_classes=("url",), use_markup=True, label=f'<a href="{l}" class="url">{l}</a>'))
            header.get_last_child().connect("activate-link", open_link)
    return reply
def catalog_activate(m, c, b):
    if not hasattr(c, "o"):
        c = c.get_first_child()
    post_engine = engines[app.sites[c.s]["Engine"].get_selected_item().get_string()]
    site_engine = engines[app.sites[site_row.get_selected_item().get_string()]["Engine"].get_selected_item().get_string()]
    o = f"parent:{c.o['ID']}" if "fetch_thread" in site_engine else c.o
    match b:
        case 1:
            if app.sites[c.s]["Launch Sources"].get_active():
                to_launch = c.o["Source"] if c.o["Source"] else c.file if c.o["File URL"].startswith("file://") and os.path.exists(c.file.peek_path()) else c.o["File URL"]
                print("Launching", to_launch)
                launch(to_launch)
            else: tab_load(q=[o, 1, c.s, []])
        case 2: Tab(q=o, s=c.s)
        case 3: c.favorite.emit("clicked")
def catalog_load_more(sw, p):
    content = sw if hasattr(sw, "count") else sw.get_parent()
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
    site_row.set_selected(sites.find(q[2]))
    page_row.set_value(q[1])
    if not isinstance(q[0], list):
        app.modifying = True
        search.set_text(f"id:{q[0]['ID']}" if isinstance(q[0], dict) else q[0])
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
    if "open-current" in a.get_name(): return launch(app.data_folder if not app.sites[q[2]]["URL"].get_text() else app.sites[q[2]]["URL"].get_text() + engines[app.sites[q[2]]["Engine"].get_selected_item().get_string()]["get_url"](q) + app.sites[q[2]]["Append to Search"].get_text())
    if isinstance(q[0], dict) and not hasattr(t.get_child().get_child(), "favorite"):
        tab_load(t)
        return GLib.idle_add(lambda *_: tab_operation(a, t=t))
    if hasattr(t.get_child().get_child(), "favorite"):
        if "favorite" in a.get_name(): t.get_child().get_child().favorite.emit("clicked")
    else:
        if "favorite" in a.get_name():
            q = q[0]
            getattr(preferences, "Bookmarks").tags = [i for i in getattr(preferences, "Bookmarks").tags if not i == q] if q in getattr(preferences, "Bookmarks").tags else [i for i in getattr(preferences, "Bookmarks").tags] + [q]
            Toast(f"{q} {'added to' if q in getattr(preferences, 'Bookmarks').tags else 'removed from'} bookmarks", timeout=2)
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
    tab_context_menu.append(("Remove Favorite" if tuple(i for i in app.data["Sites"][q[2]]["Favorites"] if i["ID"] == q[0]["ID"]) else "Add Favorite") if isinstance(q[0], dict) else ("Remove Bookmark" if q[0] in getattr(preferences, "Bookmarks").tags else "Add Bookmark"), "app.context-favorite")
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
    if not page and hasattr(content, "q") and content.q == q: return
    GLib.idle_add(apply_colors)
    e = app.sites[q[2]]["Engine"].get_selected_item().get_string()
    if page and not (q[3] and e != "Cardboard"):
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
            if e == "Cardboard":
                q[3] = fetch_favorite_catalog(q[0], q[2])
                count, q[3] = len(q[3]), q[3][limit * (q[1] - 1):] if q[1] > 1 else q[3]
            else:
                try:
                    count, q[3] = fetch_online(q[2], q[0], q[1], not page)
                except Exception as e:
                    Toast(e)
                    GLib.timeout_add(200, t.set_loading, False)
                    return GLib.idle_add(t.get_child().set_child, Adw.StatusPage(description=f"{e}", icon_name="dialog-error-symbolic", title="Error!"))
            catalog = q[3][:limit]
            if not page: GLib.idle_add(t.set_title, f"{q[0]} ({count}) ({q[2]})")
        elif isinstance(q[0], dict):
            catalog = (q[0],)
    if "parent:" in q[0] and "fetch_thread" in engines[app.sites[q[2]]["Engine"].get_selected_item().get_string()]:
        box = Gtk.Box(css_name="thread", orientation=Gtk.Orientation.VERTICAL)
        for i in q[3]: GLib.idle_add(box.append, Reply(i, q[2], q[3]))
        content = Gtk.ScrolledWindow(child=Gtk.Viewport(scroll_to_focus=False, child=box))
    else:
        q[3] = tuple(i for i in q[3] if not i in catalog)
        if not catalog and not page:
            content = Adw.StatusPage(description=f"No posts for page {q[1]}\nTry a different search", icon_name="edit-find-symbolic", title="No Results")
        elif len(catalog) == 1 and not page:
            content = Post(catalog[0][0] if isinstance(catalog[0], tuple) else catalog[0], catalog[0][1] if isinstance(catalog[0], tuple) else q[2])
            m = f"post {content.o['ID']} ({content.s})"
            print(f'{GLib.DateTime.new_now_local().format("%R")} in {m}')
            GLib.idle_add(t.set_title, m)
        else:
            if page:
                content.count[0] = min(limit * q[1], content.count[1])
            else:
                content = MasonryBox(activate=catalog_activate)
                t.viewport = content.get_child()
                content.count = [min(limit * q[1], count), count]
                content.get_child().connect("edge-reached", catalog_load_more)
            for i in catalog:
                if any(it in get_property(i, "tags", i[1]) for it in getattr(preferences, "Blacklist").tags): continue
                GLib.idle_add(masonrybox_add, *(content, Post(i[0] if e == "Cardboard" else i, i[1] if e == "Cardboard" else q[2], True)))
            total_pages = -(-content.count[1] // limit)
            m = f"Page {q[1]} of {total_pages}"
            Toast(m, message=f'{GLib.DateTime.new_now_local().format("%R")} in {q[2]} "{q[0]}" {m}', timeout=1)
    content.q = q
    GLib.idle_add(t.get_child().set_child, content)
    GLib.timeout_add(200, t.set_loading, False)
    GLib.timeout_add(200, suggestions_popover.popdown)
    if t.get_child().get_mapped():
        GLib.idle_add(site_row.set_selected, sites.find(q[2]))
        GLib.idle_add(page_row.set_value, q[1])
def Tab(*_, q=None, p=1, s="", a=False):
    t = view.get_selected_page()
    if a or not t:
        tab = view.append(Adw.Bin())
    else:
        tab = view.insert(Adw.Bin(), (view.get_n_pinned_pages() if t.get_pinned() else 1) + view.get_page_position(t))
    q, s = getattr(preferences, "New Tab Query").get_text() if q == None else q, s if s else getattr(preferences, "New Tab Site").get_selected_item().get_string()
    tab.set_title(f"post {q['ID']} ({s})" if isinstance(q, dict) else f"{q} ({s})")
    tab.history, tab.index = [[q, p, s, ()]], 0
    return tab
Action("new-tab", Tab, "<primary>t")
overview.connect("create-tab", Tab)

edit = Adw.PreferencesDialog(content_height=530, content_width=530, search_enabled=True)
pages = tuple(Adw.PreferencesPage(icon_name=f"{i}-symbolic", title=t) for i, t in (("tag-outline", "Tags"), ("folder-documents", "Post")))
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
    if os.path.exists(p.file.peek_path()) and os.path.exists(p.preview_file.peek_path()): launch(p.preview_file if p.p else p.file, folder=True)
    else:
        view.get_selected_page().set_loading(True)
        for f, u in ((p.preview_file, p.o["Preview URL"]), (p.file, p.o["File URL"])):
            Toast(f"Downloading {u}", timeout=1)
            app.session.send_and_read_async(Soup.Message.new("GET", u), GLib.PRIORITY_DEFAULT, None, post_finish_download, (p, f))
Action("download", lambda *_: post_download(view.get_selected_page().get_child().get_child()) if hasattr(view.get_selected_page().get_child().get_child(), "favorite") else None, "<primary>s")
download = Adw.ButtonRow()
download.add_css_class("suggested-action")
map_download = lambda: download.set_title("Open" if os.path.exists(edit.p.preview_file.peek_path()) and os.path.exists(edit.p.file.peek_path()) else "Download")
download.connect("activated", lambda *_: post_download(edit.p))
group.add(download)
pages[1].add(group)
dates = tuple(DateRow(title=i) for i in ("Added", "Created At"))
rating_group = Adw.ToggleGroup(name="Rating", valign=Gtk.Align.CENTER)
notes = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, css_classes=("notes",))
editable = ((TagRow(title="Tags"), "tags"),
            (Adw.EntryRow(title="Hash"), "text"),
            (Adw.EntryRow(title="Source"), "text"),
            (Adw.EntryRow(title="File URL"), "text"),
            (Adw.EntryRow(title="Preview URL"), "text"),
            (Adw.ComboRow(title="Site", model=sites), "selected-item"),
            (rating_group, "active"),
            (Adw.SpinRow(title="ID", adjustment=Gtk.Adjustment.new(0, 0, 1e20, 1, 10, 10)), "value"),
            (Adw.SpinRow(title="Parent ID", adjustment=Gtk.Adjustment.new(0, 0, 1e20, 1, 10, 10)), "value"),
            (Adw.SwitchRow(title="Has Children"), "active"),)
editable[0][0].connect("tag-widget-added", tag_widget_added)
for i in ratings: rating_group.add(Adw.Toggle(label=i[:1], tooltip=i))
def sync_post(*_):
    if app.modifying or not edit.get_mapped(): return
    app.modifying = True
    p = edit.p
    p.o["Notes"] = notes.get_buffer().get_property("text")
    for l in (editable, dates):
        for i in l:
            w, prop = i.calendar if hasattr(i, "calendar") else i[0], "date" if hasattr(i, "calendar") else i[1]
            r = w.get_ancestor(Adw.PreferencesRow)
            if r.get_title() == "Site":
                old_s, new_s = p.s, r.get_selected_item().get_string()
                if old_s != new_s and p.o in app.data["Sites"][old_s]["Favorites"]:
                    app.data["Sites"][old_s]["Favorites"].remove(p.o)
                    app.data["Sites"][new_s]["Favorites"].append(p.o)
                p.s = new_s
            else:
                v = w.get_property(prop)
                p.o[r.get_title()] = v.to_utc().to_unix() if isinstance(v, GLib.DateTime) else int(v) if isinstance(v, float) else v
    app.data["Sites"][p.s]["Favorites"] = [p.o if i["ID"] == p.o["ID"] else i for i in app.data["Sites"][p.s]["Favorites"]]
    app.modifying = False
for i in dates: i.calendar.connect(f"notify::date", sync_post)
for i in editable: i[0].connect(f"notify::{i[1]}", sync_post)
notes.get_buffer().connect(f"notify::text", sync_post)
for i in (tuple(i[0] for i in editable[1:]), dates):
    group = Adw.PreferencesGroup()
    for it in i:
        if isinstance(it, Adw.PreferencesRow): group.add(it)
        elif isinstance(it, Adw.ToggleGroup): (r := Adw.ActionRow(title=it.get_name()), r.add_suffix(it), group.add(r))
    pages[1].add(group)

group = Adw.PreferencesGroup(separate_rows=True)
ai_tag_button = Adw.ButtonRow(title="AI Autotag", css_classes=("button", "activatable", "suggested-action"), tooltip_text="Upload to Danbooru AI Tagger")
def ai_ai(b):
    form_data = Soup.Multipart.new("multipart/form-data")
    picture = edit.p
    while not hasattr(picture, "get_paintable"):
        picture = picture.get_child()
    form_data.append_form_file("file", "image.png", "image/png", picture.get_paintable().get_current_image().save_to_png_bytes())
    form_data.append_form_string("format", "json")
    mes = Soup.Message.new_from_multipart("https://autotagger.donmai.us/evaluate", form_data)
    b = app.session.send_and_read(mes)
    if mes.get_status() == 200:
        editable[0][0].tags = [i for i in json(b.get_data())[0]["tags"]]
        Toast(title=f"Tags updated", timeout=2)
    else: Toast(title=f"Server returned {mes.get_status()}!")
ai_tag_button.connect("activated", ai_ai)
group.add(Adw.PreferencesRow(activatable=False, selectable=False, css_name="notes", child=Gtk.Label(label="Notes", halign=Gtk.Align.CENTER)))
group.add(Adw.PreferencesRow(child=notes))
group.add(ai_tag_button)
group.add(editable[0][0])
pages[0].add(group)

def show_edit(b, *_):
    if app.modifying: return
    app.modifying = True
    edit.p = p = b.get_ancestor(Gtk.Overlay)
    map_download()
    notes.get_buffer().set_text(p.o["Notes"])
    for i in dates: i.calendar.set_date(GLib.DateTime.new_from_unix_utc(p.o[i.get_title()]))
    for i in editable:
        if isinstance(i[0], Adw.ComboRow) and i[0].get_title() == "Site": i[0].set_selected(sites.find(p.s))
        else: i[0].set_property(i[1], p.o[i[0].get_ancestor(Adw.PreferencesRow).get_title()])
    edit.present(app.window)
    app.data["Sites"][p.s]["Favorites"] = [p.o if i["ID"] == p.o["ID"] else i for i in app.data["Sites"][p.s]["Favorites"]]
    app.modifying = False

css_selector = regex(r"[^a-zA-Z0-9-_]|^(?=\d)")
def apply_colors(*_):
    t = view.get_selected_page()
    v = t.get_child()
    while hasattr(v, "get_child"):
        v = v.get_child()
    v = v.get_paintable() if hasattr(v, "get_paintable") else v
    s = t.history[t.index][2]
    GLib.idle_add(set_colors, v, True)
    if not hasattr(app.window, "classes"): setattr(app.window, "classes", ())
    for i in app.window.classes: GLib.idle_add(app.window.remove_css_class, i)
    app.window.classes = (f"{css_selector.sub('_', app.sites[s]['Engine'].get_selected_item().get_string())}", f"{css_selector.sub('_', s)}")
    for i in app.window.classes: GLib.idle_add(app.window.add_css_class, i)
    return False

for i in app.data["Tabs"]: view.set_page_pinned(Tab(q=i[0], p=i[1], s=i[2], a=True), i[3])
if not view.get_selected_page(): Tab()
getattr(preferences, "Post Colors Theming").bind_property("active", Action("colors", apply_colors, stateful=False), "state", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, lambda b, v: GLib.Variant("b", v))
GLib.idle_add(tab_changed)
app.run()
if not app.shutdown: data_save(True)
