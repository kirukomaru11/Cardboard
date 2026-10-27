try:
    from Utils import *
except ModuleNotFoundError:
    try:
        from .Utils import *
    except ModuleNotFoundError:
        print("No Utils")
        import sys
        sys.exit()

from os import urandom
from os.path import commonprefix
from re import compile as Regex, DOTALL
from html import unescape as html_unescape
from html.parser import HTMLParser

from sqlite3 import register_adapter
def datetime_adapter(d): return d.to_utc().to_unix()
from json import loads as json, dumps as json_dumps
def json_default(o): return datetime_adapter(o) if isinstance(o, GLib.DateTime) else o
def json_string(o): return json_dumps(o, default=json_default)
register_adapter(dict, json_string)
register_adapter(list, json_string)
register_adapter(tuple, json_string)
register_adapter(GLib.DateTime, datetime_adapter)

class Window(Window):
    __gtype_name__ = "Window"
    drop_target_gtypes = (Gdk.FileList, Gio.File, Gtk.Label)
    prev_button = GObject.Property(type=Gtk.Button)
    next_button = GObject.Property(type=Gtk.Button)
    search = GObject.Property(type=Gtk.Widget)
    stack = GObject.Property(type=Gtk.Stack)
    wide = GObject.Property(type=Adw.ToolbarView)
    narrow = GObject.Property(type=Adw.ToolbarView)
    context_tab = GObject.Property(type=Adw.TabPage)
    context = GObject.Property(type=Gtk.Widget)

    def __init__(self, _id=None, tab=False):
        super().__init__()
        self.stack = Gtk.Stack()
        self.search = Search()
        self.wide, self.narrow = [Adw.ToolbarView(content=Adw.LayoutSlot.new("stack")) for _ in range(2)]
        if not _id: App.default.data.set_default(table="Windows", conditions="ID = ?", conds=(self.get_id(),), names=("ID", ), values=(self.get_id(),))
        elif self.get_id() != _id: App.default.data.update(table="Windows", column="ID", value=self.get_id(), conditions="ID = ?", conds=(_id,))
        self.next_button = Button(icon_name="go-next", tooltip_text="Next", callback=Tab.nav_history, sensitive=False)
        self.prev_button = Button(icon_name="go-previous", tooltip_text="Back", callback=Tab.nav_history, sensitive=False)
        multi = Adw.MultiLayoutView()
        bookmarks_view, view = tuple(Adw.TabView(menu_model=Tab.context_menu) for _ in range(2))
        for i in (view, bookmarks_view): self.stack.add_child(i)
        for i, w in (("stack", self.stack), ("search", self.search), ("start", Gtk.Box()), ("menu", Button(t=Gtk.MenuButton, menu_model=self.__class__.menu, tooltip_text="Menu", icon_name="open-menu"))): multi.set_child(i, w)
        for i in (self.prev_button, self.next_button): multi.get_child("start").append(i)
        wide_header = Adw.HeaderBar(title_widget=Adw.Clamp(hexpand=True, child=Adw.LayoutSlot.new("search"), maximum_size=650))
        narrow_header = Adw.HeaderBar(show_title=False, show_end_title_buttons=False)
        self.wide.add_top_bar(wide_header)
        for i in (Adw.LayoutSlot.new("search"), narrow_header): self.narrow.add_bottom_bar(i)
        for i in ("Default Width", "Default Height"): App.default.data.persist_action(self, i, 1, "Windows", i, "ID = ?", (self.get_id(),)).bind_property("state", self, i.lower().replace(" ", "-"), SYNC_BIND, unpack_bind, variant_bind)
        App.default.data.persist_action(self, "Manga Width", 1, "Windows", "Manga Width", "ID = ?", (self.get_id(),))
        App.default.data.persist_action(self, "Maximized", False, "Windows", "Maximized", "ID = ?", (self.get_id(),)).bind_property("state", self, "maximized", SYNC_BIND, unpack_bind, variant_bind)
        App.default.data.persist_action(self, "Second View", True, "Windows", "Second View", "ID = ?", (self.get_id(),))
        for i, n in ((self.wide, "wide"), (self.narrow, "narrow")):
            ToolbarFullscreen(i)
            multi.add_layout(Adw.Layout(content=i, name=n))
        App.default.data.persist_action(self, "Fullscreen", False, "Windows", "Fullscreen", "ID = ?", (self.get_id(),)).connect("notify::state", self.change_fullscreen)
        for i in (wide_header, narrow_header):
            i.pack_start(Adw.LayoutSlot.new("start"))
            i.pack_end(Adw.LayoutSlot.new("menu"))
        wide_header.pack_start(Button(icon_name="tab-new", tooltip_text="New Tab", action_name="app.new-tab"))
        for i in App.default.data.read(table="Tabs", conditions="Window = ?", conds=(self.get_id(),), return_dict=True, force_tuple=True):
            try:
                q = json(i["Query"])
                if not "File URL" in q:
                    q = i["Query"]
            except:
                q = i["Query"]
            Tab.create(view=bookmarks_view if i["TabView"] == 2 else view, query=q, page=i["Page"], board=i["Board"])
        if not tab and not self.stack.get_first_child().get_selected_page(): Tab.create(view=self.stack.get_first_child())
        for i in self.stack:
            i.bar = Adw.TabBar(autohide=i != bookmarks_view, view=i)
            if i == bookmarks_view:
                i.bar.get_first_child().bind_property("reveal-child", self.stack.get_first_child().bar, "autohide", INVERT_BIND)
                self.lookup_action("second-view").bind_property("state", i.bar.get_first_child(), "reveal-child", SYNC_BIND, unpack_bind, variant_bind)
            self.wide.add_top_bar(i.bar)
            i.overview = Adw.TabOverview(child=multi if i == view else view.overview, enable_new_tab=True, view=i, secondary_menu=Window.menu)
            i.overview.connect("create-tab", self.__class__.overview_create_tab)
            tb = Adw.TabButton(view=i)
            if i == bookmarks_view: self.lookup_action("second-view").bind_property("state", tb, "visible", SYNC_BIND, unpack_bind, variant_bind)
            tb.connect("clicked", self.__class__.tab_button_clicked)
            narrow_header.pack_start(tb)
            i.set_menu_model(Tab.context_menu)
            i.connect("notify::selected-page", Tab.changed)
            i.connect("notify::n-pages", Tab.idle_save_all)
            i.connect("page-reordered", Tab.idle_save_all)
            i.connect("setup-menu", Tab.setup_menu)
            i.connect("create-window", self.__class__.create)
            i.connect("close-page", Tab.operation)
        b = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(Adw.BreakpointConditionLengthType.MAX_WIDTH, 700, Adw.LengthUnit.PX))
        for i in ("apply", "unapply"): b.connect(i, self.update_css_size)
        b.add_setter(multi, "layout-name", "narrow")
        self.add_breakpoint(b)
        self.stack.connect("notify::visible-child", self.__class__.child_changed)
        self.__class__.child_changed(self.stack, None)
        bookmarks_view.bar.get_first_child().connect("notify::reveal-child", self.__class__.reveal_bookmarks_bar)
        self.set_content(self.stack.get_last_child().overview)
        self.change_fullscreen()
        Task.invoke(bookmarks_view.bar.get_first_child().set_reveal_child, self.lookup_action("second-view").get_state().unpack())
        Task.invoke(self.__class__.reveal_bookmarks_bar, bookmarks_view.bar.get_first_child())
        self.present()

    @staticmethod
    def on_gesture_drag_drag_begin(e, x, y):
        if e.get_current_button() != 1: return
        self = e.get_widget()
        w = self.pick(x, y, Gtk.PickFlags.DEFAULT)
        self.drag_begin = None if not w or not w.get_ancestor(Manga) else w
        self.last_drag_value = (0, 0)
        if self.drag_begin: self.drag_begin.set_cursor(Gdk.Cursor.new_from_name("ew-resize", None))

    @staticmethod
    def on_gesture_drag_drag_update(e, x, y):
        if e.get_current_button() != 1: return
        self = e.get_widget()
        if getattr(self, "drag_begin", False) and getattr(self, "last_drag_value", None):
            px, py = self.last_drag_value
            v = self.get_root().lookup_action("manga-width").get_state().unpack() + x - px
            self.get_root().lookup_action("manga-width").set_state(GLib.Variant("i", max(100, v)))
        self.last_drag_value = x, y

    @staticmethod
    def on_gesture_drag_drag_end(e, x, y):
        self = e.get_widget()
        if getattr(self, "drag_begin", False): self.drag_begin.set_cursor(None)
        self.drag_begin = self.last_drag_value = None

    @staticmethod
    def on_key_pressed(e, v, kc, s):
        self = e.get_widget().get_root()
        if v == Gdk.KEY_Escape:
            if self.search.autocomplete.get_mapped(): return
            if self.search.boards and self.search.boards.get_mapped():
                self.search.boards.popdown()
                return True
            if "toolbar-fullscreen" in self.get_css_classes() and self.search.get_ancestor(Gtk.Revealer).get_reveal_child():
                self.search.get_ancestor(Gtk.Revealer).set_reveal_child(False)
                return True
        if isinstance(self.get_focus(), Gtk.Editable) or isinstance(self.get_focus(), Gtk.TextView):
            if v == Gdk.KEY_Return and self.get_focus().get_ancestor(Search):
                if self.get_focus() != self.search.query: return self.search.text_activate(self.search, None, s)
            return
        content = self.stack.get_visible_child().get_selected_page().get_child().get_child() if self.stack.get_visible_child().get_selected_page() else False
        if content and Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_e:
            if isinstance(content, Post):
                PostEditor.show([content])
                return True
            if hasattr(content, "get_posts"):
                posts = [i for i in content.get_posts() if "selected" in i.get_css_classes()]
                if posts:
                    PostEditor.show(posts)
                    return True
        if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_a and hasattr(content, "get_posts"):
            if all("selected" in i.get_css_classes() for i in content.get_posts()):
                for i in content.get_posts(): i.remove_css_class("selected")
            else:
                for i in content.get_posts(): Task.invoke(i.add_css_class, "selected")
            return True
        if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_v:
            c = self.get_display().get_clipboard()
            if c.get_formats().contain_gtype(Gdk.FileList):
                c.read_value_async(Gdk.FileList, GLib.PRIORITY_LOW, None, self.__class__.clipboard_read_value)
                return True
            elif "gchararray" in c.get_formats().to_string():
                c.read_text_async(None, self.__class__.clipboard_read_text)
                return True
        return handle_scroll(content, v, s) if content else None

    def update_css_size(self, b):
        if not self.get_current_breakpoint(): Task.invoke(self.add_css_class, "small")
        else: Task.invoke(self.remove_css_class, "small")

    @staticmethod
    def on_map(w): Tab.changed(w.stack.get_visible_child())

    @staticmethod
    def on_drop_target_drop(e, v, x, y):
        self = e.get_widget().get_root()
        if hasattr(self, "highlight") and self.highlight:
            self.highlight.remove_css_class("highlight")
            a, b = Boards.list.default.get_model()[v.get_label()], Boards.list.default.get_model()[self.highlight.get_label()]
            if a == b: return False
            a.id, b.id = b.id, a.id
            s = Boards.list.default.get_sorter()
            Boards.list.default.set_sorter(None)
            Boards.list.default.set_sorter(s)
            self.highlight = None
            return True
        else:
            open_files([v] if isinstance(v, Gio.File) else v)
            return True

    @staticmethod
    def on_drop_target_motion(e, x, y):
        self = e.get_widget().get_root()
        if getattr(self, "highlight", False): self.highlight.remove_css_class("highlight")
        self.highlight = self.get_widget_at_popover(self.search.boards, x, y)
        if self.highlight and not self.highlight.get_ancestor(Gtk.Button):
            self.highlight.add_css_class("highlight")
            return Gdk.DragAction.MOVE
        self.highlight = None
        return Gdk.DragAction.COPY

    @staticmethod
    def reveal_bookmarks_bar(a, p=None): GLib.timeout_add(200, a.get_ancestor(Adw.TabBar).get_template_child(Adw.TabBar, "scrolled_window").get_hadjustment().set_value, 0)

    @staticmethod
    def tab_button_clicked(b):
        if not b.get_view().get_n_pages(): Tab.create(view=b.get_view())
        b.get_view().get_parent().set_visible_child(b.get_view())
        b.get_view().overview.set_open(not b.get_view().overview.get_open())

    @staticmethod
    def overview_create_tab(*_): return Tab.create().tab

    @staticmethod
    def on_click(e, *args):
        self = e.get_widget().get_root()
        b = e.get_current_button()
        if isinstance(e, Gtk.GestureClick):
            n, x, y, signal = args
        else:
            x, y, signal = args
        if b == 8:
            if signal == "released": Task.invoke(self.prev_button.emit, "clicked")
            return
        elif b == 9:
            if signal == "released": Task.invoke(self.next_button.emit, "clicked")
            return
        if self.search.autocomplete.get_mapped():
            if signal == "released": self.search.autocomplete.popdown()
            return
        w = self.pick(x, y, Gtk.PickFlags.DEFAULT)
        if self.search.boards.get_mapped():
            w = self.get_widget_at_popover(self.search.boards, x, y)
            if not (w and w.get_ancestor(Search)): self.search.boards.popdown()
            return
        if (isinstance(e, Gtk.GestureClick) and b == 3 or isinstance(e, Gtk.GestureLongPress) and b == 1) and w and w.get_ancestor(Search):
            if isinstance(e, Gtk.GestureClick) and Gdk.ModifierType.SHIFT_MASK in e.get_current_event_state(): return
            self.show_popover_at_widget(self.search.boards, self.search, x, y)
            e.set_state(Gtk.EventSequenceState.CLAIMED)
            Task.invoke(e.reset)
        if isinstance(e, Gtk.GestureClick) and signal == "pressed" or isinstance(e, Gtk.GestureLongPress) and b != 1: return
        if not w or w.get_ancestor(Chapters) or w.get_ancestor(Gtk.Button): return
        if w.get_ancestor(Adw.TabBar): return self.stack.set_visible_child(w.get_ancestor(Adw.TabBar).get_view())
        if w.get_ancestor(Post):
            w = w.get_ancestor(Post)
        if not isinstance(w.get_parent(), Tab) and Gdk.ModifierType.CONTROL_MASK in e.get_current_event_state() and b == 1: return Context.action(post=w, action="Toggle Select")
        if not (isinstance(w, Post) or isinstance(w, Gtk.Picture)): return
        if b == 1 and isinstance(w, Post) and not (isinstance(e, Gtk.GestureLongPress) and "small" in self.get_css_classes()):
            if w.media and isinstance(w.media.picture, Picture) and any(i.get_mapped() for i in w.media.picture.get_parent() if isinstance(i, Gtk.Scrollbar)): return
            if isinstance(e, Gtk.GestureLongPress): PostEditor.show([w])
            elif w.get_ancestor(Reply):
                if w.launch_url: launch(w.launch_url)
                elif w.media:
                    if w.preview != w.full:
                        if w.get_paintable(displaying=True) == w.preview:
                            if w.full: w.finish_func(w.full, w.media)
                            else:
                                w.media.picture.set_paintable(Adw.SpinnerPaintable.new(w))
                                w.task = Post.start_task(w.media, w.get_uri(), media_stream_args={"volume": 0.8})
                        else:
                            if w.preview: w.finish_func(w.preview, w.media)
                            else:
                                w.media.picture.set_paintable(Adw.SpinnerPaintable.new(w))
                                w.task = Post.start_task(w.media, w.get_preview_uri())
            elif w.source and w.read_board("Launch Sources"): launch(w.source)
            elif not any(w in i.posts for i in PostEditor.get_all() if i.posts): w.toggle_favorite()
        elif b == 2: Context.action(post=w, action="Open in New Tab")
        elif (b == 3 or isinstance(e, Gtk.GestureLongPress)) and (w.get_ancestor(Manga) and isinstance(w, Gtk.Picture) or w.get_ancestor(Post)):
            p = w.get_ancestor(Thread) or w.get_ancestor(Catalog) or w.get_ancestor(Manga)
            posts = [i for i in p.get_posts() if "selected" in i.get_css_classes()] if "selected" in w.get_css_classes() and hasattr(p, "get_posts") else [w]
            menu = Menu()
            me = {"Open": [], "Launch": ["Get Source"], "Copy": ["Copy Picture"] if hasattr(w, "get_paintable") and w.get_paintable() else [], "Rest": ["Reload"]}
            if isinstance(w.get_parent(), Tab): me["Open"].append("Open in New Tab")
            else:
                me["Open"].extend(("Open", "Open in New Tab"))
                for i in ["Unselect" if "selected" in w.get_css_classes() else "Select", "Unselect All" if p.get_posts() and all("selected" in i.get_css_classes() for i in p.get_posts()) else "Select All"]: menu.append(i, f"app.context::{i}")
                if len(posts) > 1:
                    me["Launch"].append("Get Selection Sources")
                    me["Open"].extend(["Open Selection as Manga", "Open Selection in New Tabs", "Open Selection Sources in New Tabs",])
                    me["Launch"].append("Launch Selection Sources")
                    me["Copy"].append("Copy Selection Sources")
                    if all(isinstance(i, Post) for i in posts):
                        me["Launch"].append("Launch Selection File URLs")
                        me["Copy"].append("Copy Selection File URLs")
                        for i in ["Favorite Selection", "Unfavorite Selection", "Toggle Favorite for Selection", "Properties for Selection"]: menu.append(i, f"app.context::{i}")
            if isinstance(w, Post):
                me["Open"].extend(["Open Source", "Open File URL"])
                me["Launch"].extend(["Launch Source", "Launch File URL"])
                me["Rest"].extend(["Unfavorite" if w.exists() else "Favorite", "Properties"])
                if w.uri.startswith("file://"): me["Copy"].append("Copy File")
                me["Copy"].extend(["Copy Source", "Copy File URL"])
            else: me["Launch"].append("Launch Source")
            for i in tuple(i for i in me["Open"]):
                if not i.endswith(("New Tab", "New Tabs")) and not i + " in New Tab" in me["Open"]: me["Open"].append(i + " in New Tab")
            for k, v in me.items():
                if not v: continue
                if k == "Rest": menu.parse({"!": Menu(dict((i, f"context::{i}") for i in v))})
                elif k == "Open":
                    _m = menu if len(v) == 1 else Menu({k: dict((i, f"context::{i}") for i in v)})
                    if isinstance(w, Post):
                        rel = [f"{k} {i} in New Tab" for i in [i for i in [w.source if "_" in w.id and w.source.split("/artworks/")[-1].strip() == w.id.split("_")[0] else None, w.source.strip("/") + "/" if "pinterest.com/pin/" in w.source else None, w.get_thread(), w.get_chapters(), w.get_chapter()] + [i for i in w.tags if i.startswith(("https://", "http://", "file://"))] + [" + ".join([i for i in w.tags if i.startswith("parent:")])] if i]]
                        _m.parse({"!": Menu(dict((i, f"app.context::{i}") for i in rel))})
                    if _m != menu: menu.append_section(None, _m)
                elif len(v) == 1: menu.parse({v[0]: f"context::{v[0]}"})
                else: menu.append_submenu(k, Menu(dict((i, f"app.context::{i}") for i in v)))
            self.context = self.context or Context()
            self.context.set_menu_model(menu)
            self.context.post = w
            self.show_popover_at_widget(self.context, w, x, y)

    @staticmethod
    def on_drag_source_prepare(e, x, y):
        self = e.get_widget().get_root()
        w = self.get_widget_at_popover(self.search.boards, x, y)
        if w and not w.get_ancestor(Gtk.Button):
            e.v = [w]
            e.set_actions(Gdk.DragAction.MOVE)
            return Gdk.ContentProvider.new_for_value(w)
        w = self.pick(x, y, Gtk.PickFlags.DEFAULT)
        e.v = []
        for i in (Post, Gtk.Picture):
            if w.get_ancestor(i):
                w = w.get_ancestor(i)
        if w and w.get_ancestor(Manga):
            w = None
        if isinstance(w, Post):
            if w.media and isinstance(w.media.picture, Picture) and any(i.get_mapped() for i in w.media.picture.get_parent() if isinstance(i, Gtk.Scrollbar)):
                w = None
                e.v = []
            if w and w.get_file() and exists(w.get_file()): e.v.append(Gdk.FileList.new_from_list((Gio.File.new_for_uri(w.get_file()),)))
            elif hasattr(w, "file_url") and "://" in w.file_url: e.v.append(Gdk.FileList.new_from_list((Gio.File.new_for_uri(w.file_url),)))
        if hasattr(w, "get_paintable") and w.get_paintable() and not isinstance(w.get_paintable(), Adw.SpinnerPaintable):
            e.v.insert(0, w.get_paintable())
            v = paintable_to_value(w.get_paintable())
            if v: e.v.insert(0, v)
        c = None
        if e.v:
            e.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
            c = Gdk.ContentProvider.new_union(tuple(i if isinstance(i, Gdk.ContentProvider) else Gdk.ContentProvider.new_for_value(i) for i in e.v)) if len(e.v) > 1 else Gdk.ContentProvider.new_for_value(e.v[0])
        else: e.set_actions(Gdk.DragAction.NONE)
        e.set_content(c)
        return c

    @staticmethod
    def on_drag_source_drag_begin(e, d):
        self = e.get_widget().get_root()
        for i in e.v:
            if isinstance(i, Gdk.Paintable): return Gtk.DragIcon.get_for_drag(d).set_child(Adw.Clamp(tightening_threshold=300, maximum_size=300, orientation=Gtk.Orientation.VERTICAL, child=Adw.Clamp(css_name="media", margin_top=10, margin_start=10, tightening_threshold=300, maximum_size=300, child=Gtk.Picture.new_for_paintable(i))))
            if isinstance(i, Gdk.FileList): return Gtk.DragIcon.get_for_drag(d).set_child(Gtk.Label(margin_top=10, margin_start=10, label=i[0].get_uri(), css_classes=("title-4",), ellipsize=Pango.EllipsizeMode.END))
            if isinstance(i, Gtk.Label): Gtk.DragIcon.get_for_drag(d).set_child(Gtk.Label(margin_top=10, margin_start=10, label=i.get_label(), css_classes=("title-4",), ellipsize=Pango.EllipsizeMode.END))

    @staticmethod
    def on_drag_source_drag_end(e, d, de):
        self = e.get_widget().get_root()
        e.set_content(None)
        e.set_actions(Gdk.DragAction.NONE)
        if hasattr(self, "highlight") and self.highlight: self.highlight.remove_css_class("highlight")

    @staticmethod
    def create(*_): return Window(tab=True).stack.get_visible_child()

    @staticmethod
    def child_changed(s, p):
        for i in s:
            if i == s.get_visible_child(): Task.invoke(i.bar.add_css_class, "visible")
            else: Task.invoke(i.bar.remove_css_class, "visible")
        if s.get_root(): Task.invoke(Tab.changed, s.get_visible_child())

    @staticmethod
    def clipboard_read_value(cl, r):
        v = cl.read_value_finish(r)
        open_files([v] if isinstance(v, Gio.File) else v)

    @staticmethod
    def clipboard_read_text(cl, r): open_files(cl.read_text_finish(r).split("\n"))

class Tab(Adw.Bin):
    __gtype_name__ = "Tab"
    history = GObject.Property(type=object)
    index = GObject.Property(type=int, minimum=0)
    tab = GObject.Property(type=Adw.TabPage)
    closed = []

    context_menu = Menu({"!a": Menu({"New Tab": "new-tab", "New Window": "new-window", "Reopen Closed Tab": "reopen-tab"}), "!b": Menu({"Move to Other View": "context-move-or-fav", "Close Tab": "context-close"})})

    def __init__(self, view, query, page, board):
        super().__init__(css_name=self.__gtype_name__.lower(), focusable=True)
        v = view or Window.current.stack.get_visible_child()
        view = view or Window.current.stack.get_first_child()
        current_tab = v.get_selected_page().get_child() if v and v.get_selected_page() else False
        self.tab = view.add_page(self, current_tab.tab if current_tab else None) if view.get_mapped() else view.append(self)
        q = [query, page, board, ()]
        q2 = current_tab.get_current_query() if current_tab and current_tab.history else ["", 1, "Favorites", ()]
        for n, i in enumerate(q2):
            if q[n] == False:
                q[n] = i
        if current_tab and isinstance(current_tab.get_child(), Post) and (query == False or query == current_tab.get_current_query()[0]):
            q[0] = current_tab.get_child().get_dict()
            self.history = [q]
            self.load(paintable=current_tab.get_child().get_paintable())
        else:
            self.history = [q]
            self.update_title()

    def get_current_query(self):
        if self.history and len(self.history) > self.index: return self.history[self.index]
        return ["", 1, "Favorites", ()]

    def set_current_query(self, q):
        if not self.history:
            self.history = [self.get_current_query()]
            self.index = 0
        self.history[self.index] = q

    def get_page(self): return self.get_current_query()[1]

    def set_page(self, p=1):
        q = self.get_current_query()
        q[1] = p
        self.set_current_query(q)

    def sync(self, paintable=None):
        if self.history == None: return
        q = self.get_current_query()
        w = self.get_root()
        if not w or not self.get_mapped(): return False
        if isinstance(q[0], str): w.search.set_text(q[0])
        elif isinstance(q[0], dict):
            if "ID" in q[0]: w.search.set_text(f"id:{q[0]['ID']}")
            elif "File URL" in q[0]: w.search.set_text(q[0]["File URL"])
        w.prev_button.set_sensitive(len(self.history) - 1 >= self.index and self.index != 0)
        w.next_button.set_sensitive(len(self.history) > self.index + 1)
        w.search.page = q[1]
        w.search.boards.set_selected(q[2])
        for i in Boards:
            if i.name == q[2]: Task.invoke(w.add_css_class, i.name)
            else: Task.invoke(w.remove_css_class, i.name)
        for i in Board.engines: w.remove_css_class(i.get_string() if not i.get_string()[0].isdigit() else "_" + i.get_string())
        if hasattr(self.get_child(), "engine"): Task.invoke(w.add_css_class, self.get_child().engine if not self.get_child().engine[0].isdigit() else "_" + self.get_child().engine)
        if isinstance(self.get_child(), Thread):
            for i in self.get_child().get_posts(): Task.invoke(i.set_size)
        if paintable:
            v = paintable
        elif isinstance(self.get_child(), Adw.Spinner):
            v = None
        else:
            v = self.pick(self.get_width() / 2, self.get_height() / 2, Gtk.PickFlags.DEFAULT)
        if isinstance(v, Gtk.Widget) and not isinstance(v, Post):
            v = v.get_ancestor(Post) or v
        Task.invoke(Palette.set_colors, v if hasattr(v, "colors") else v.get_paintable() if hasattr(v, "get_paintable") else None)

    def update_title(self):
        if self.history == None: return
        q = self.get_current_query()
        if isinstance(q[0], dict):
            if "ID" in q[0]:
                t = f"post {q[0]['ID']}"
            elif "File URL" in q[0]:
                if isinstance(q[0]["File URL"], list):
                    t = f"{len(q[0]['File URL'])} URLs"
                else:
                    t = str(q[0]["File URL"])
        else:
            t = str(q[0])
        if hasattr(self.get_child(), "total") and isinstance(self.get_child().total, int) and self.get_child().total > 0:
            t += f" ({self.get_child().total})"
        self.tab.set_title(t.strip() + f" ({q[2]})")

    def content(self, q, engine, data, paintable, next_page):
        child = None
        if next_page:
            child = self.get_child()
            Task.invoke(child.load_page, q, data)
        else:
            if isinstance(q[0], str) and not q[3]:
                child = Adw.StatusPage(icon_name="edit-find-symbolic", title="No Results")
            elif q[3] and isinstance(q[0], str) and is_thread(q[0], engine):
                child = Thread(q)
            post = q[0] if isinstance(q[0], dict) else None
            if not post and len(q[3]) == 1:
                post = q[3][0]
            if not child and post:
                if "Chapters" in post:
                    child = Chapters(post["Chapters"], data=data)
                elif "File URL" in post and (isinstance(post["File URL"], list) or post["File URL"].endswith(".cbz")):
                    child = Manga(post)
                else:
                    post.setdefault("Board", q[2])
                    child = Post(post, parent=self, paintable=paintable)
            if not child:
                child = Catalog(q, data)
            if not child.get_parent() == self: self.set_child(child)
        child.q = q
        child.engine = engine
        Task.invoke(self.update_title)
        GLib.timeout_add(200, self.tab.set_loading, False)
        if self.get_mapped():
            Task.invoke(self.sync)
            Task.invoke(self.grab_focus)
        if self.get_mapped(): GLib.timeout_add(200, Tab.idle_save_all)

    @staticmethod
    def create(*_, view=False, query=False, page=False, board=False): return Tab(view if isinstance(view, Adw.TabView) else False, query, page, board)

    @staticmethod
    def setup_menu(v, t): v.get_root().set_property("context-tab", t)

    @staticmethod
    def nav_history(b):
        tab = b.get_root().stack.get_visible_child().get_selected_page().get_child()
        if not b.get_sensitive() or not tab: return
        if "next" in b.get_icon_name():
            if not tab.history or tab.index >= len(tab.history): return tab.sync()
        else:
            if tab.index == 0: return tab.sync()
        tab.index += (1 if "next" in b.get_icon_name() else -1)
        tab.load(history=True)

    def grab_focus(self): Task.invoke(self.get_child().grab_focus)

    @staticmethod
    def changed(view, *_):
        if not view.get_mapped(): return
        w = view.get_root()
        if not view.get_selected_page(): return
        self = view.get_selected_page().get_child()
        if not self.history: return
        if self.get_child():
            Task.invoke(self.sync)
            Task.invoke(self.grab_focus)
        else: Task.invoke(self.load)
        for p, w in get_paintables(widgets=True).items():
            if isinstance(p, MediaStream) and not p.volume > 0.0: Task.invoke(setattr, p, "playing", any(i.get_mapped() for i in w))

    def load(self, history=False, query=False, page=False, board=False, paintable=None, next_page=False):
        self.next_page = next_page
        self.paintable = paintable
        q = [query, page, board, ()]
        for n, i in enumerate(self.get_current_query()):
            if q[n] == False:
                q[n] = i
        if not history:
            if not next_page and q != self.get_current_query():
                self.index = len(self.history) or 1
                self.history.append(q)
            if not next_page and not paintable and hasattr(self.get_child(), "q") and self.get_child().q == q: return False
        if not next_page:
            self.unload()
            self.set_child(Adw.Spinner())
        self.tab.set_loading(True)
        Extractor(self)
        return False

    def unload(self):
        child = self.get_child()
        c = [child] + ([i for i in child.get_posts()] if hasattr(child, "get_posts") else [])
        editors = PostEditor.get_all()
        for i in c:
            if isinstance(i, Post) and any(i in it.posts for it in editors): continue
            if hasattr(i, "do_dispose"): Task.invoke(i.do_dispose)
            if isinstance(i, Media): Task.invoke(i.do_dispose)
            if isinstance(i, Gtk.Picture):
                if hasattr(i.get_paintable(), "pause"): Task.invoke(i.get_paintable().pause)
                Task.invoke(i.set_paintable, None)
            if hasattr(i, "unparent") and i.get_parent(): Task.invoke(i.unparent)
            i = None

    @staticmethod
    def operation(a, b=False, t=False):
        view = a if isinstance(a, Adw.TabView) else App.default.get_active_window().stack.get_visible_child()
        if not t:
            t = b if isinstance(b, Adw.TabPage) else view.get_root().context_tab if "context" in a.get_name() else view.get_selected_page()
            t = t.get_child()
        if not t: return
        view = t.get_ancestor(Adw.TabView)
        if isinstance(a, Adw.TabView) or isinstance(a, Gio.SimpleAction) and "close-tab" in a.get_name():
            Task.invoke(view.close_page, t.tab) if isinstance(a, Gio.SimpleAction) else None
            if t.history and not t.get_current_query() in Tab.closed: Tab.closed.append(t.get_current_query())
            Task.invoke(App.default.lookup_action("reopen-tab").set_enabled, bool(Tab.closed))
            Task.invoke(t.unload)
        if "move-or-fav" in a.get_name():
            if not "context" in a.get_name() and isinstance(t.get_child(), Post): t.get_child().toggle_favorite()
            else:
                nv = view.get_next_sibling() if view.get_next_sibling() != None else view.get_prev_sibling()
                view.transfer_page(t.tab, nv, nv.get_n_pages())

    @staticmethod
    def idle_save_all(*_): Task.invoke(Tab.get_all, save=True)

    @staticmethod
    def get_all(save=False):
        tabs = []
        for w in App.default.get_windows():
            if not isinstance(w, Window) or save and not w.get_mapped(): continue
            for __id, v in enumerate(w.stack):
                for ___id, i in enumerate(v.get_pages()):
                    if save:
                        i.get_child().data = (w.get_id(), __id, ___id)
                    tabs.append(i.get_child())
        if save and Window.current and Window.current.get_mapped():
            if not all(i.history for i in tabs): return
            for i in tabs:
                if i.data[1] == 0 and i.data[2] == 0: App.default.data.delete(table="Tabs", conditions="Window = ?", conds=(i.data[0],))
                q = i.get_current_query()
                App.default.data.new(table="Tabs", values=(i.data[0], i.data[1] + 1, i.data[2] + 1, q[0], q[1], q[2]))
        return tabs

class Catalog(Masonry):
    __gtype_name__ = "Catalog"

    total = GObject.Property(type=int, default=0)

    def __init__(self, *args):
        super().__init__()
        self.connect("edge-reached", self.__class__.load_more)
        Task.invoke(self.load_page, *args)

    def get_posts(self): return tuple(i for i in self if isinstance(i, Post))

    def load_more(self, p=3):
        if p == 3 and not self.get_parent().tab.get_loading():
            if isinstance(self.count, int) and not self.q[3] and (self.total == 0 and self.count == 0 or self.q[1] >= total_pages(self.total, self.count)): return
            if not self.q[3] and not self.count == "end" or self.q[3] and self.count == "end":
                self.q[1] += 1
                self.get_parent().set_current_query(self.q)
                self.get_parent().sync()
            if self.q[3]: return self.add_posts()
            if not self.count == "end": self.get_parent().load(next_page=True)

    def load_page(self, q=None, data=0):
        self.q = q
        if isinstance(data, tuple):
            self.count, self.total = data
        elif self.total == 0:
            self.count = data
        if data == "end" and self.total == 0:
            self.total = len(self.q[3]) + len(self.get_posts())
        self.add_posts()
        if self.get_ancestor(Tab): self.get_ancestor(Tab).update_title()

    def add_posts(self, n=0):
        n += 1
        c = self.q[3][:25]
        if not c or n == 4: return
        self.q[3] = tuple(i for i in self.q[3] if not i in c)
        if not self.get_parent(): return Task.invoke(self.add_posts, n=n)
        self.get_parent().set_current_query(self.q)
        for i in c:
            i.setdefault("Board", self.q[2])
            Post(i, parent=self)
        m = f"{current_page(len(self.get_posts()), 25)} of {total_pages(len(self.q[3]) + len(self.get_posts()), 25)}"
        if isinstance(self.count, int) and self.total >= 1:
            m += f" ({self.q[1]} of {total_pages(self.total, self.count)})"
        Toast(m, timeout=1)

class PostData(Gtk.Overlay):
    __gtype_name__ = "PostData"

    @GObject.Property(type=str, default="Favorites")
    def board(self): return getattr(self, "_board", "")

    @board.setter
    def board(self, value):
        old = self.board
        if old == value: return
        if old and self.exists():
            if PostData.exists({"Board": value, "ID": self.id}):
                Toast(f"post {self.id} ({value}) already exists")
                return
            App.default.data.update(table="Posts", column="Board", value=value, conditions="Board = ? AND ID = ?", conds=(old, self.id))
        self._board = value

    @GObject.Property(type=str, default="Example")
    def id(self): return getattr(self, "_id", "")

    @id.setter
    def id(self, value):
        old = self.id
        if old == value: return
        if old and self.exists():
            if PostData.exists({"Board": self.board, "ID": value}):
                Toast(f"post {value} ({self.board}) already exists")
                return
            App.default.data.update(table="Posts", column="ID", value=value, conditions="Board = ? AND ID = ?", conds=(self.board, old))
        self._id = value

    source = GObject.Property(type=str)
    tags = GObject.Property(type=GObject.Strv, default=[])
    notes = GObject.Property(type=str)
    added = GObject.Property(type=GLib.DateTime)
    created_at = GObject.Property(type=GLib.DateTime)
    file_url = GObject.Property(type=str)

    def __init__(self, post={}, **kwargs):
        super().__init__(**kwargs)
        self.id = post.get("ID", "Example") or "Example"
        self.board = post.get("Board", "Favorites") or "Favorites"
        self.source = post.get("Source", "")
        self.tags = post.get("Tags", [])
        self.notes = post.get("Notes", "")
        self.added = GLib.DateTime.new_from_unix_utc(post["Added"]) if "Added" in post else GLib.DateTime.new_now_utc()
        self.created_at = GLib.DateTime.new_from_unix_utc(post["Created At"]) if "Created At" in post else GLib.DateTime.new_now_utc()
        self.file_url = post.get("File URL", "")
        for i in self.__class__.default:
            if i.name in ("board", "id"): continue
            self.connect(f"notify::{i.name}", self.__class__.changed)

    def exists(self):
        if isinstance(self, PostData):
            b, i = self.board, self.id
        else:
            b, i = self.get("Board", "Favorites"), self.get("ID", "Example")
        return App.default.data.exists(table="Posts", conditions="Board = ? AND ID = ?", conds=(b, i))

    def toggle_favorite(self):
        for i in ("removing", "adding"): self.remove_css_class(i)
        e = self.exists()
        if e: App.default.data.delete(table="Posts", conditions="Board = ? AND ID = ?", conds=(self.board, self.id))
        else:
            o = self.get_dict()
            App.default.data.new(table="Posts", values=tuple(o.values()), names=o.keys())
            if self.read_board("Download Favorites"): Task.invoke(self.download, True)
        Task.invoke(self.add_css_class, "removing" if e else "adding")
        GLib.timeout_add((GLib.TIME_SPAN_SECOND * 2) / 1000, self.set_styles)

    def get_dict(self): return dict((i, Gtk.Overlay.get_property(self, v.name)) for i, v in PostData.default_titles.items())

    def get_file(self): return self.file_url if self.file_url.startswith("file://") else ("file://" + Path(App.default.data_folder.peek_path(), self.board, self.id))

    def get_preview_file(self):
        p = self.get_preview_url()
        return self.get_file() if not p else p if p.startswith("file://") else ("file://" + Path(App.default.data_folder.peek_path(), self.board, f"p-{self.id}"))

    def get_uri(self):
        file = self.get_file()
        return file if exists(file) else self.file_url

    def get_preview_uri(self):
        file, preview_file, preview_url = self.get_file(), self.get_preview_file(), self.get_preview_url() or self.file_url
        return preview_file if exists(preview_file) else file if exists(file) else preview_url if preview_url else self.file_url

    def get_preview_url(self=""):
        if isinstance(self, str):
            u = self
            self = None
        else:
            u = self.file_url
        if not u: return
        if u.startswith("file://"): return u
        if u.startswith("https://t1."): return u.replace("https://t1.", "https://t2.")
        if u.startswith("https://i.pximg.net/img-original/img/"): return u.replace("/img-original/img/", "/c/600x1200_90_webp/img-master/img/").replace(".png", ".jpg").replace(".jpg", "_master1200.jpg")
        if u.startswith("https://arch-img"):
            u = u.replace("arch-img", "arch").replace("dev", "dev/media")
            ts = u.split("/")[-1].split(".")[0]
            if len(ts) >= 16:
                ts = ts[:13]
            return u.rsplit("/", 1)[0] + f"/thumb/{ts[:4]}/{ts[4:6]}/{ts}s.jpg"
        if u.startswith("https://img.youtube.com/"): return u.replace("maxresdefault", "mqdefault")
        if u.startswith("https://pbs.twimg.com/"): return u.replace("orig", "small")
        if u.startswith("https://i.pinimg.com/"): return u.replace("originals", "1200x").replace(".png", ".jpg").replace(".webp", ".jpg")
        if u.startswith("https://rvideos") and "memedroid.com/" in u: return u.replace(".mp4", ".jpeg")
        if u.startswith("https://img.ifunny.co/") and u.endswith("_1.mp4"): return u.replace("videos", ",/images").replace("img.", "imageproxy.").replace("_1.mp4", "_3.jpg")

        if self and "https://i.4cdn.org/" in u and "spoiler" in self.tags: return f"https://s.4cdn.org/image/spoiler-{u.rsplit('/', 1)[0].split('/')[-1]}1.png"
        if "https://i.4cdn.org/" in u and not u.endswith("s.jpg"): return u.rsplit(".", 1)[0] + "s.jpg"
        if "/data/" in u and not "thumbnail" in u and len("".join(u.split("/data/", 1)[-1].split("/", 2)[:2])) == 4 and not Gio.content_type_guess(u)[0].startswith("video"): return f"https://img.{u.split('://', 1)[-1].split('.', 1)[-1]}".replace("/data/", "/thumbnail/data/")
        if "artstation.com" in u: return u.replace("4k", "small")
        if "https://mangadex.org/covers/" in u: return u.replace(".512.jpg", "") + ".512.jpg"
        if len(u.replace("sample-", "").split("/")[-1].split(".")[0]) == 32:
            if ("/original/" in u or "/sample/" in u): return (u.replace("original", "720x720").replace("/sample/", "/720x720/").replace("sample-", "").rsplit(".", 1)[0] + ".webp")
            if "images" in u: return ("/thumbnail_".join((u.replace("images", "thumbnails").rsplit(".", 1)[0] + ".jpg").rsplit("/", 1)))
        if "/data/image/" in u: return u.replace("/data/image/", "/data/preview/").rsplit(".", 1)[0] + ".jpg"
        elif "/data/" in u and len(u.split("/data/")[-1].split(".")[0]) == 32: return u.replace("/data/", "/data/preview/").rsplit(".", 1)[0] + ".jpg"
        if "/image/" in u:
            md5 = u.split("/image/")[-1].split("/")[0]
            if len(md5) == 32:
                u = u.rsplit("/", 1)[0].replace("/image/", "/data/preview/") + ".jpg"
                if "yande.re" in u:
                    u = f"preview/{md5[:2]}/{md5[2:4]}/".join(u.split("preview/"))
                return u
            else: return u.replace("image", "thumb").rsplit(".", 1)[0] + "s.jpg"
        if self and "/src/" in u and "spoiler" in self.tags: return f"{u.split('/src/')[0].rsplit('/', 1)[0]}/static/spoiler.svg"
        if "/src/" in u: return u.replace("/src/", "/thumb/").rsplit(".", 1)[0] + "." + ("jpg" if Gio.content_type_guess(u)[0].startswith("video") else u.rsplit(".", 1)[-1])

    def read_board(self, c): return getattr(Boards.list.default.get_model()[self.board], c.lower().replace(" ", "_"), "")

    def get_chapter(self): return (self.source.strip("/") + "/") if is_chapter(self.source) else None

    def get_chapters(self):
        v = None
        if is_chapters(self.source.strip("/") + "/"):
            if self.source.startswith("https://weebcentral.com"):
                v = self.source.rsplit("/", 1)[0]
            else:
                v = (self.source.strip("/") + "/")
        return v

    def get_thread(self):
        b = Boards.list.default.get_model()[self.board]
        return self.source if b and is_thread(self.source, b.engine) else None

    @staticmethod
    def changed(self, p):
        if isinstance(self, Post):
            Task.invoke(self.automatic_tags)
            Task.invoke(self.set_styles)
        if not self.exists(): return
        App.default.data.update(table="Posts", column=self.__class__.prop_get_title(p.get_name()), value=GObject.Object.get_property(self, p.get_name()), conditions="Board = ? AND ID = ?", conds=(self.board, self.id))

    @staticmethod
    def prop_get_name(p): return (p if isinstance(p, str) else p.name).replace("-", "_")
    @staticmethod
    def prop_get_title(p): return (p if isinstance(p, str) else p.name).replace("-", " ").replace("_", " ").title().replace("Url", "URL").replace("Id", "ID")

PostData.default = [i for i in PostData.list_properties() if i.owner_type.pytype == PostData]
PostData.default_names = dict((PostData.prop_get_name(i), i) for i in PostData.default)
PostData.default_titles = dict((PostData.prop_get_title(i), i) for i in PostData.default)

class PostEditor(PopupDialog):
    __gtype_name__ = "PostEditor"
    bindings = GObject.Property(type=object)
    posts = GObject.Property(type=object)
    tags = GObject.Property(type=TagRow)
    id = GObject.Property(type=Adw.EntryRow)
    board = GObject.Property(type=Adw.ComboRow)
    source = GObject.Property(type=URIRow)
    file_url = GObject.Property(type=URIRow)
    notes = GObject.Property(type=Adw.PreferencesRow)
    added = GObject.Property(type=DateRow)
    created_at = GObject.Property(type=DateRow)

    download = GObject.Property(type=Adw.ButtonRow)

    def __init__(self, posts):
        page = GroupsPage()
        toolbar = Adw.ToolbarView(content=page)
        header = Adw.HeaderBar()
        header.pack_end(PopupDialogButton())
        toolbar.add_top_bar(header)
        super().__init__(content=toolbar, dialog_kwargs={"content_width": 600, "content_height": 600}, window_kwargs={"default_width": 600, "default_height": 600})
        for i in (self.window, self.dialog): Window.controller_init(i)
        self.posts = posts

        group = Adw.PreferencesGroup()
        self.tags = TagRow(activate=self.__class__.tag_clicked)
        group.add(self.tags)
        group.add(Button(t=Adw.ButtonRow, callback=self.__class__.ai_autotag, title="AI Autotag", start_icon_name="tag"))
        page.add(group)

        group = Adw.PreferencesGroup()
        self.id = Adw.EntryRow(title="ID")
        group.add(self.id)
        e = Gtk.PropertyExpression.new(Gtk.StringObject, None, "string")
        self.board = Adw.ComboRow(title="Board", enable_search=True, search_match_mode=Gtk.StringFilterMatchMode.SUBSTRING, expression=e)
        group.add(self.board)
        page.add(group)

        group = Adw.PreferencesGroup()
        self.source = URIRow(title="Source", placeholder="Source", multiple=False)
        group.add(self.source)
        self.file_url = URIRow(title="File URL", placeholder="File URL", multiple=False)
        group.add(self.file_url)
        self.download = Button(t=Adw.ButtonRow, callback=self.__class__.download)
        self.download.connect("map", self.__class__.map_download)
        group.add(self.download)
        page.add(group)

        group = Adw.PreferencesGroup()
        self.notes = TextRow(title="Notes")
        self.notes.add_css_class("notes")
        group.add(self.notes)
        page.add(group)

        group = Adw.PreferencesGroup()
        self.added = DateRow(title="Added")
        group.add(self.added)
        self.created_at = DateRow(title="Created At")
        group.add(self.created_at)
        page.add(group)
        self.start()
        self.present()

    def on_click(e, *args):
        self = PostEditor.get_self(e.get_widget())
        b = e.get_current_button()
        if b != 2: return
        if isinstance(e, Gtk.GestureClick):
            n, x, y, signal = args
        else: return
        w = self.pick(x, y, Gtk.PickFlags.DEFAULT)
        if not w or isinstance(w, Gtk.Button) or w.get_ancestor(Gtk.Button): return
        if w.get_ancestor(Adw.HeaderBar): self.close()

    def on_key_pressed(e, v, kc, s):
        if v == Gdk.KEY_Escape: e.get_widget().get_root().close()

    def unbind(self):
        if self.bindings:
            for i in self.bindings:
                if isinstance(i, tuple): i[0].disconnect(i[1])
                else: i.unbind()
        self.bindings = []

    def start(self):
        self.unbind()
        if not self.posts: return
        if len(self.posts) == 1:
            post = self.posts[0]
            self.set_title(f"Post {post.id} ({post.board})")
            self.board.set_property("model", Gtk.StringList.new([i.name for i in Boards]))
            self.bindings.append(post.bind_property("board", self.board, "selected", SYNC_BIND, selected_bind, self.__class__.board_bind))
            self.bindings.append(post.bind_property("id", self.id, "text", SYNC_BIND))
            self.bindings.append(post.bind_property("created-at", self.created_at, "date", SYNC_BIND))
            self.bindings.append(post.bind_property("added", self.added, "date", SYNC_BIND))
            self.bindings.append(post.bind_property("source", self.source, "text", SYNC_BIND))
            self.bindings.append(post.bind_property("file-url", self.file_url, "text", SYNC_BIND))
            self.bindings.append(post.bind_property("notes", self.notes, "text", SYNC_BIND))
            self.bindings.append(post.bind_property("tags", self.tags, "tags", SYNC_BIND))
            if "colored" in post.get_root().get_css_classes(): self.window.add_css_class("colored")
            else: self.window.remove_css_class("colored")
        else:
            self.set_title(f"{len(self.posts)} posts")
            l = [i.name for i in Boards]
            b = self.posts[0].board
            for i in self.posts:
                if i.board != b:
                    b = None
                    l.insert(0, "Different")
                    break
            self.board.set_property("model", Gtk.StringList.new(l))
            if b == None: self.board.set_selected(0)
            else: self.board.set_selected(self.board.get_property("model").find(b))
            self.bindings.append((self.board, self.board.connect("notify::selected", self.__class__.board_changed)))
            self.id.set_text("".join(self.__class__.split_common([i.id for i in self.posts])))
            self.bindings.append((self.id, self.id.connect("notify::text", self.__class__.id_changed)))
            for p in ("source", "file_url", "notes"):
                w = getattr(self, p)
                w.set_text("".join(self.__class__.split_common([getattr(i, p) for i in self.posts])))
                self.bindings.append((w, w.connect("notify::text", self.__class__.text_changed)))
            self.bindings.append((self.added, self.added.connect("notify::date", self.__class__.date_changed)))
            self.bindings.append((self.created_at, self.created_at.connect("notify::date", self.__class__.date_changed)))
            tags = [i.tags for i in self.posts]
            l = list(set(tags[0]).intersection(*tags[1:]))
            if any(len(i.tags) != len(l) for i in self.posts): l.append("{{Different}}")
            self.tags.tags = l
            self.bindings.append((self.tags, self.tags.connect("notify::tags", self.__class__.tags_changed)))
            self.window.remove_css_class("colored")

    @staticmethod
    def tags_changed(b, p):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        tags = [i.tags for i in self.posts]
        common = list(set(tags[0]).intersection(*tags[1:]))
        new = [i for i in b.tags if not i == "{{Different}}" and not i in common]
        d = "{{Different}}" in b.tags
        for p in self.posts:
            l = [i for i in p.tags if not (i in common and not i in b.tags)] + new
            if not d:
                l = [i for i in l if i in b.tags]
            p.tags = l

    @staticmethod
    def split_common(strings):
        prefix = commonprefix(strings)
        max_suffix_len = min(len(s) - len(prefix) for s in strings)
        suffix = ""
        for i in range(max_suffix_len):
            chars = {s[-1-i] for s in strings}
            if len(chars) != 1: break
            suffix = next(iter(chars)) + suffix
        d = "" if all(i == suffix + prefix for i in strings) else "{{Different}}"
        return [prefix, d, suffix]

    @staticmethod
    def date_changed(b, p):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        if b == self.added:
            for i in self.posts:
                i.added = b.date
        if b == self.created_at:
            for i in self.posts:
                i.created_at = b.date

    @staticmethod
    def id_changed(b, p):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        prefix, d, suffix = self.__class__.split_common([i.id for i in self.posts])
        if d and not d in b.get_text():
            Toast(f"Nothing done! {d} not found!")
            return
        if d:
            nprefix, nsuffix = b.get_text().split(d, 1)
        else:
            nprefix, nsuffix = b.get_text(), ""
        ids = [self.__class__.get_new(i.id, prefix, nprefix, suffix, nsuffix, d) for i in self.posts]
        for n, i in enumerate(self.posts):
            if i.id != ids[n]:
                if PostData.exists({"Board": i.board, "ID": ids[n]}): return Toast(f"Nothing Done! {ids[n]} ({i.board}) already exists!")
        for n, i in enumerate(self.posts):
            i.id = ids[n]

    @staticmethod
    def text_changed(b, p):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        p = b.get_title().lower().replace(" ", "_")
        prefix, d, suffix = self.__class__.split_common([getattr(i, p) for i in self.posts])
        if d and not d in b.get_text():
            Toast(f"Nothing done! {d} not found!")
            return
        if d:
            nprefix, nsuffix = b.get_text().split(d, 1)
        else:
            nprefix, nsuffix = b.get_text(), ""
        for n, i in enumerate(self.posts): setattr(i, p, self.__class__.get_new(getattr(i, p), prefix, nprefix, suffix, nsuffix, d))

    @staticmethod
    def get_new(o, prefix, nprefix, suffix, nsuffix, d):
        if d:
            no = o
            if prefix:
                no = no.split(prefix,1)[-1]
            if nprefix:
                no = nprefix + no
            if suffix:
                no = no.rsplit(suffix, 1)[0]
            if nsuffix:
                no += nsuffix
            return no
        else: return nprefix + nsuffix

    @staticmethod
    def board_changed(b, p):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        bo = self.posts[0].board
        for i in self.posts:
            if i.board != bo:
                bo = None
                break
        if bo == None and b.get_selected() == 0: return
        else:
            board = b.get_selected_item().get_string()
            posts = [i for i in self.posts if i.board != board]
            if any(PostData.exists({"Board": board, "ID": i.id}) for i in posts): return Toast(f"Nothing done! post {i.id} ({board}) already exists")
            for i in posts:
                i.board = board
            Task.invoke(self.start)

    @staticmethod
    def board_bind(b, v):
        self = PostEditor.get_self(b.get_property("target"))
        if not self or not self.posts: return b.get_property("source").get_property(b.get_property("source-property"))
        if len(self.posts) == 1: return b.get_property("target").get_selected_item().get_string()

    def show(posts):
        p = False
        for i in PostEditor.get_all():
            if posts == i.posts:
                p = i
        if p: return p.present(Window.current)
        else: PostEditor(posts)

    @staticmethod
    def tag_clicked(w, b):
        self = PostEditor.get_self(w)
        if not self or not self.posts: return
        if len(self.posts) != 1: return
        window = self.posts[0].get_root()
        if not window: return
        view = window.stack.get_visible_child()
        match b:
            case 1: view.get_selected_page().get_child().load(query=w.tag, page=1, board=self.posts[0].board)
            case 2: Tab.create(view=window.stack.get_first_child(), query=w.tag, page=1, board=self.posts[0].board)

    @staticmethod
    def map_download(b):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        files = []
        for i in self.posts:
            files.append(i.get_file())
            if i.read_board("Download Thumbnails"): files.append(i.get_preview_file())
        if all(exists(i) for i in files): b.set_properties(title="Open", start_icon_name="document-open-symbolic")
        else: b.set_properties(title="Download", start_icon_name="folder-download-symbolic")

    @staticmethod
    def download(b):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        for i in self.posts: i.download()

    @staticmethod
    def ai_autotag(b):
        self = PostEditor.get_self(b)
        if not self or not self.posts: return
        for i in self.posts:
            paintable = i.get_paintable()
            if not paintable: return Toast("No paintable")
            try:
                i.tags = [i for i in json(Online.MultipartRequest("https://autotagger.donmai.us/evaluate", fields={"format": "json"}, files=[("file", "image.png", "image/png", paintable_get_texture(paintable.get_current_image()).save_to_png_bytes())]).decode())[0]["tags"]]
                Toast("Tags updated")
            except Exception as e: print(e, "Could not update tags")
        self.start()

    def do_dispose(self):
        Task.invoke(PopupDialog.do_dispose, self)
        if self.posts:
            for i in self.posts:
                if not i.get_parent(): Task.invoke(i.do_dispose)
        self.posts = None
        Task.invoke(self.unbind)

    def get_all(): return [i for i in PopupDialog.get_all() if isinstance(i, PostEditor)]

class Post(PostData):
    __gtype_name__ = "Post"

    before = GObject.Property(type=Adw.Bin)
    preview = GObject.Property(type=Gdk.Paintable)
    full = GObject.Property(type=Gdk.Paintable)
    media = GObject.Property(type=Media)

    launch_url = GObject.Property(type=str)

    def __init__(self, o, paintable=None, parent=None):
        launch_url = None
        if "embed" in o and type(o["embed"]) == str:
            launch_url = o["embed"].split('href="', 1)[-1].split('"', 1)[0]
        comment = Reply.get_prop(o, "comment")
        replies = int(o.get("replies", 0) or o.get("nreplies", 0) or 0)
        new = {}
        for i in PostData.default_titles: new.setdefault(i, o.get(i, None))
        for k, default in PostData.default_titles.items():
            if k in ("Added", "Created At"):
                if not isinstance(new[k], int):
                    new[k] = GLib.DateTime.new_now_utc().to_unix()
            elif k == "ID":
                if new[k] == None:
                    _id = 1
                    for i in App.default.get_active_window().stack.get_first_child().get_pages():
                        i = i.get_child()
                        if isinstance(i.get_child(), Post) and i.get_child().board == o["Board"] and i.get_child().id.isdigit() and int(i.get_child().id) >= _id:
                            _id = int(i.get_child().id) + 1
                    if parent:
                        for i in parent:
                            if isinstance(i, Post):
                                if i.board == o["Board"] and i.id.isdigit() and int(i.id) >= _id:
                                    _id = int(i.id) + 1
                    while App.default.data.exists(table="Posts", conditions="Board = ? AND ID = ?", conds=(o["Board"], _id)):
                        _id = int(_id) + 1
                    _id = int(_id)
                    new[k] = str(_id)
                elif not type(new[k]) == str:
                    new[k] = str(new[k])
            elif k == "Board":
                new[k] = o["Board"]
            elif k == "Tags":
                if type(new[k]) == str:
                    new[k] = json(new[k])
            elif type(default.default_value) != type(new[k]):
                new[k] = default.default_value
        o = new
        super().__init__(post=o, css_name=self.__gtype_name__.lower(), overflow=Gtk.Overflow.HIDDEN)
        self.launch_url = launch_url
        self.before = Adw.Bin(css_name="before", focusable=False, limit_events=True, sensitive=False, can_target=False, can_focus=False, focus_on_click=False, hexpand=True, vexpand=True)
        self.add_overlay(self.before)
        if parent:
            if isinstance(parent, Masonry): parent.add(self)
            elif hasattr(parent, "append"): parent.append(self)
            elif hasattr(parent, "set_child"): parent.set_child(self)
        self.uri = self.get_uri() if isinstance(self.get_parent(), Tab) else self.get_preview_uri()
        if self.get_ancestor(Reply) or self.get_ancestor(Adw.WrapBox): self.set_halign(Gtk.Align.START)
        if self.get_ancestor(Adw.WrapBox): self.set_valign(Gtk.Align.START)
        if self.uri:
            self.media = Media(zoom=isinstance(parent, Tab), vexpand=True, hexpand=True, overflow=Gtk.Overflow.HIDDEN)
            if isinstance(parent, Masonry):
                if replies: self.add_overlay(Gtk.Label(css_name="replies", halign=Gtk.Align.START, valign=Gtk.Align.START, vexpand=True, label=str(replies)))
                if comment:
                    self.set_child(Gtk.Box(orientation=Gtk.Orientation.VERTICAL))
                    for i in (self.media, Adw.Clamp(css_name="intro", maximum_size=100, orientation=Gtk.Orientation.VERTICAL, child=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, max_content_height=150, propagate_natural_height=True, child=Gtk.Viewport(valign=Gtk.Align.CENTER, child=Comment(comment, {"yalign": 0, "justify": Gtk.Justification.CENTER,}, { "halign": Gtk.Align.CENTER}))), valign=Gtk.Align.END)): self.get_child().append(i)
                else: self.set_child(self.media)
            else: self.set_child(self.media)
            paintables = get_paintables() + ([paintable] if paintable else [])
            paintable = next((i for i in paintables if i.uri == self.uri), False)
            if paintable:
                paintable.set_volume(0.8 if isinstance(parent, Tab) else 0.0)
                Task.invoke(self.__class__.finish_func, paintable, self.media)
            else:
                self.task = self.start_task(self.media, self.uri, media_stream_args={"volume": 0.8 if isinstance(parent, Tab) else 0.0})
        else:
            if comment: self.set_child(Comment(comment, {"yalign": 0, "justify": Gtk.Justification.CENTER,}, { "halign": Gtk.Align.CENTER}))
            else: self.set_child(Gtk.Label(label=o["Notes"] if o["Notes"] else f"Post {self.id} ({self.board})\nNo notes or file URL", wrap=True, justify=Gtk.Justification.CENTER))
            Task.invoke(self.automatic_tags)
            Task.invoke(self.set_styles)
        if self.exists() and self.read_board("Download Favorites"): Task.invoke(self.download, True)

    def do_dispose(self):
        if hasattr(self.full, "pause"): Task.invoke(self.full.pause)
        if hasattr(self.preview, "pause"): Task.invoke(self.preview.pause)
        if self.media: Task.invoke(self.media.do_dispose)
        for it in ("media", "full", "preview"): Task.invoke(setattr, self, it, None)

    def grab_focus(self):
        if self.media: Task.invoke(self.media.grab_focus)

    @staticmethod
    def start_task(widget, uri, headers=None, media_stream_args=None):
        headers = headers or {}
        if any(i in uri for i in (".donmai.us", "mangadex.org")): headers.update({"User-Agent": "Cardboard"})
        return PaintableTask(func=Post.finish_func, data=widget, uri=uri, media_stream_args=media_stream_args, headers=headers)

    def automatic_tags(self):
        t, defaults = [], ["absurdres", "animated", "animated_gif", "highres", "incredibly_absurdres", "lowres", "missing_file", "missing_thumbnail", "sound", "tagme", "tall_image", "video", "wide_image"]
        uri = self.get_uri()
        if uri:
            mimetype = Gio.content_type_guess(uri)[0]
            if self.full:
                if isinstance(self.full, MediaStream):
                    if self.full.duration > 1: t.append("animated")
                    if self.full.has_audio: t.append("sound")
                if mimetype.startswith("video"): t.append("video")
                if mimetype == "image/gif" and "animated" in t: t.append("animated_gif")
                if mimetype == "image/png" and "animated" in t: t.append("animated_png")
                full = get_paintable(self.full)
                w, h = full.get_intrinsic_width(), full.get_intrinsic_height()
                if max(w, h) > 10000: t.append("incredibly_absurdres")
                if w >= 3200 and h >= 2400: t.append("absurdres")
                if w >= 1600 and h >= 1200: t.append("highres")
                if 500 >= w and 500 >= h: t.append("lowres")
                if h >= 1024 and 0.25 >= (w / h): t.append("tall_image")
                if w >= 1024 and (w / h) >= 4: t.append("wide_image")
            else:
                if mimetype.startswith("audio"): t.append("sound")
                if mimetype.startswith("video"): t.extend(["animated", "sound", "video"])
                if mimetype == "image/gif": t.extend(["animated", "animated_gif"])
        else: t.append("missing_file")
        if "https://img.youtube.com/" in self.get_uri() or ("youtube.com" in self.source or "youtu.be" in self.source): t.extend(["animated", "sound", "video"])
        if "https://pbs.twimg.com/" in self.source or "https://img.ifunny.co/" in self.source: t.append("source_request")
        for i in ("memedroid.com/", "ifunny.co/"):
            if i in self.source or i in self.file_url: t.append("meme")
        for i in (self.source, self.file_url):
            for it in ("steamgriddb.com", "steamstatic.com"):
                if it in i: t.append("game")
        for i in (self.source, self.file_url):
            if "tenor.com/" in i: t.extend(i.strip("/").rsplit("/", 1)[-1].replace(".mp4", "").replace(".gif", "").split("-gif-", 1)[0].split("-"))
        if self.read_board("Download Thumbnails") and (not self.get_preview_uri() or self.get_preview_uri() == self.get_uri()): t.append("missing_thumbnail")
        if "reddit.com/r/" in self.source: t.append(self.source.split("reddit.com", 1)[-1].rsplit("/comments/", 1)[0])
        if "x.com/" in self.source or "twitter.com/" in self.source: t.append(self.source.split("x.com/")[-1].split("twitter.com/")[-1].split("/", 1)[0].lower())
        def do_sort(i):
            return defaults.index(i) if i in defaults else len(defaults) + 1
        t.sort(key=do_sort)
        for i in t:
            if not i in self.tags: self.tags.append(i)
        if self.full:
            for i in defaults:
                if not i in t and i in self.tags: self.tags.remove(i)
        for i in tuple(i for i in self.tags):
            if not i: self.tags.remove(i)
        if not self.tags: self.tags.append("tagme")
        if not self.source and not "source_request" in self.tags: self.tags.append("source_request")

    def set_styles(self):
        Task.invoke(self.set_css_classes, ["selected"] if "selected" in self.get_css_classes() else [])
        for i in self.tags:
            if not i: continue
            if i.startswith("parent:"):
                if i.replace("parent:", "") == self.id: Task.invoke(self.add_css_class, "parent")
                else: Task.invoke(self.add_css_class, "child")
            try:
                Task.invoke(self.add_css_class, i)
            except: print(i, "Failed")
        if hasattr(self.get_paintable(), "duration") and self.get_paintable().duration > 1: Task.invoke(self.add_css_class, "playing")
        if self.get_paintable(): Task.invoke(self.add_css_class, "media")
        else: Task.invoke(self.add_css_class, "not-media")
        if self.get_chapters(): Task.invoke(self.add_css_class, "chapters")
        if self.get_chapter(): Task.invoke(self.add_css_class, "chapter")
        if self.get_thread(): Task.invoke(self.add_css_class, "thread")
        if self.exists(): Task.invoke(self.add_css_class, "starred")
        if bool(self.notes): Task.invoke(self.add_css_class, "has-notes")
        if self.get_uri().startswith("file://"): Task.invoke(self.add_css_class, "local")
        if self.get_preview_uri().startswith("file://"): Task.invoke(self.add_css_class, "local-preview")
        if [i for i in self if i.get_css_name() == "replies"]: Task.invoke(self.add_css_class,"has-replies")
        if isinstance(self.get_child(), Gtk.Box): Task.invoke(self.add_css_class, "has-intro")
        Task.invoke(self.add_css_class, "preview" if self.get_paintable(displaying=True) and self.get_paintable(displaying=True).uri == self.get_preview_uri() else "full")
        Task.invoke(self.add_css_class, self.board)
        Task.invoke(self.add_css_class, self.id)

    def get_paintable(self, displaying=False):
        if not displaying:
            if self.full: return self.full
            if self.preview: return self.preview
        if self.media and self.media.media_stream: return self.media.media_stream
        else: return next((i for i in (self.full, self.preview) if i and i.uri == self.uri), False)
        return False

    @staticmethod
    def finish_func(mediastream, w):
        p = w.get_ancestor(Post) or w
        if isinstance(p.get_parent(), Tab) or p.get_ancestor(Manga):
            if not hasattr(mediastream, "colors") and not (isinstance(mediastream, MediaStream) and not mediastream.has_video):
                mediastream.colors = Palette.from_paintable(mediastream)
            if p.get_mapped() and p.get_parent().get_first_child() == p: Task.invoke(p.get_ancestor(Tab).sync, mediastream)
        if isinstance(w, Media): Task.invoke(w.set_property, "media-stream", mediastream)
        if isinstance(w, Gtk.Picture): Task.invoke(w.set_paintable, mediastream)
        if hasattr(p, "set_size"): Task.invoke(p.set_size)
        if isinstance(p, Post):
            if mediastream.uri == p.get_uri():
                p.full = mediastream
            if mediastream.uri == p.get_preview_uri():
                p.preview = mediastream
            p.uri = mediastream.uri
            Task.invoke(p.automatic_tags)
            Task.invoke(p.set_styles)
            if isinstance(w, Media) and isinstance(p.get_parent(), Tab) and mediastream.duration: Task.invoke(p.controls_focus)
        m = w.get_ancestor(Masonry)
        if m: Task.invoke(m.check_layout)

    def controls_focus(self):
        if self.media and self.media.controls and isinstance(self.get_parent(), Tab): self.media.controls.playback_button.grab_focus()

    def set_size(self):
        if self.get_root() and (self.get_ancestor(Reply) or self.get_ancestor(Adw.WrapBox)):
            p = self.get_paintable(displaying=True)
            if p: Task.invoke(self.set_size_request, *clamp_size(min((self.get_root().get_height(), self.get_root().get_width())), p.get_intrinsic_width(), p.get_intrinsic_height()))

    def do_download(self, url, file):
        headers = {}
        if any(i in url for i in ("mangadex.org", ".donmai.us")): headers.update({"User-Agent": "Cardboard"})
        b = Online.Request(url, headers=headers)
        set_contents(file, contents=b)
        if self.get_root(): Task.invoke(self.get_ancestor(Tab).tab.set_loading, False)
        for i in PostEditor.get_all(): PostEditor.map_download(i.download)

    def download(self, automatic=False):
        files = [(self.get_file(), self.file_url)]
        if self.read_board("Download Thumbnails"): files.append((self.get_preview_file(), self.get_preview_url()))
        if all(exists(i[0]) for i in files):
            if automatic: return
            for i in files:
                launch(i[0], folder=True)
                return
        if self.get_root(): self.get_ancestor(Tab).tab.set_loading(True)
        for i in files:
            if not i[1]: continue
            f = Gio.File.new_for_uri(i[0])
            if not exists(f.get_parent()): f.get_parent().make_directory()
            Task(self.do_download, i[1], f).start()

class Context(Gtk.PopoverMenu):
    __gtype_name__ = "Context"

    post = GObject.Property(type=Gtk.Widget)

    def __init__(self): super().__init__(has_arrow=False)

    @staticmethod
    def activate(a, s): Context.action(post=App.default.get_active_window().context.post, action=s.unpack().strip("'"))

    @staticmethod
    def action(post=None, action=False):
        if not post: return
        if post.get_root() and post.get_root().context: post.get_root().context.popdown()
        p = post.get_ancestor(Tab)
        if not p: return
        p = p.get_child()
        board = post.board if hasattr(post, "board") else p.q[2]
        posts = [i for i in p.get_posts() if "selected" in i.get_css_classes()] if "Selection" in action else [post]
        if action == "Toggle Select":
            action = "Unselect" if "selected" in post.get_css_classes() else "Select"
        if " All" in action:
            for i in p.get_posts(): i.remove_css_class("selected") if "Unselect" in action else Task.invoke(i.add_css_class, "selected")
        elif "Select" in action and not "Selection" in action: Task.invoke(post.add_css_class, "selected")
        elif "Unselect" in action: post.remove_css_class("selected")
        elif "Properties" in action: PostEditor.show(posts)
        elif "as Manga" in action:
            q = {"query": {"File URL": [i.file_url if isinstance(i, Post) else i.get_name() for i in posts]}, "page": 1, "board": board}
            if "New Tab" in action: Tab.create(**q)
            else: post.get_ancestor(Tab).load(**q, paintable=post.get_paintable())
        else:
            qs = []
            for i in posts:
                if "Reload" in action:
                    if isinstance(i, Gtk.Picture):
                        i.set_paintable(Adw.SpinnerPaintable.new(i))
                        i.task = Post.start_task(i, i.get_name())
                    else:
                        if not i.media:
                            i.media = Media(zoom=isinstance(i.get_parent(), Tab), overflow=Gtk.Overflow.HIDDEN)
                        i.media.set_property("media-stream", None)
                        i.task = Post.start_task(i.media, i.get_uri() if isinstance(i.get_parent(), Tab) else i.get_preview_uri())
                if "Toggle Favorite" in action: i.toggle_favorite()
                elif "Favorite" in action:
                    if not i.exists(): i.toggle_favorite()
                elif "Unfavorite" in action:
                    if i.exists(): i.toggle_favorite()
                if "File URL" in action or "Get" in action and "Source" in action:
                    q = i.file_url if isinstance(i, Post) else i.get_name()
                elif "Source" in action:
                    q = (i.launch_url if i.launch_url else i.source) if isinstance(i, Post) else i.get_name()
                elif "Copy File" in action: return Gdk.Display.get_default().get_clipboard().set_content(Gdk.ContentProvider.new_for_value(Gdk.FileList.new_from_list((Gio.File.new_for_uri(post.get_file()),))))
                elif "Copy Picture" in action:
                    v = paintable_to_value(post.get_paintable())
                    if v: Gdk.Display.get_default().get_clipboard().set_content(v)
                    return
                else:
                    q = i.get_dict() if isinstance(i, Post) else {"File URL": i.get_name()}
                qs.append(q)
                if "Launch" in action: launch(q)
                elif "Get" in action and "Source" in action: launch(f"https://saucenao.com/search.php?url={q}")
                elif "Open" in action:
                    if not action in ("Open", "Open in New Tab", "Open Selection in New Tabs") and not any(i in action for i in ("File URL", "Source")):
                        q = action.replace("Open ", "").replace(" in New Tab", "")
                    if "New Tab" in action:
                        t = Tab.create(query=q, page=1, board=board)
                        if isinstance(i, Post):
                            p = i.full if hasattr(i, "full") and i.full else i.get_paintable()
                            if p and p.uri == (q if isinstance(q, str) else q["File URL"]): t.load(paintable=p)
                    else: i.get_ancestor(Tab).load(query=q, page=1, board=board, paintable=i.get_paintable() if hasattr(i, "get_paintable") else None)
            if "Copy" in action: Gdk.Display.get_default().get_clipboard().set("\n".join(qs))

class Comment(Gtk.Box):
    __gtype_name__ = "Comment"
    def __init__(self, comment, args={}, wargs={}):
        self.comment, self.args, self.wargs = comment, args, wargs
        self.args.update({"use_markup": True, "selectable": True, "wrap": True, "wrap_mode": Pango.WrapMode.WORD_CHAR})
        super().__init__(css_name=self.__gtype_name__.lower(), orientation=Gtk.Orientation.VERTICAL)
        d = ParseComment(self.comment).body
        for n, i in enumerate(d):
            if not i or len(i) == 1: continue
            if all(it["css_classes"] == i[0]["css_classes"] for it in i):
                for it in i[1:]:
                    i[0]["label"] += " " + it["label"]
                d[n] = [i[0]]
        last = None
        for w in d:
            if len(w) == 1:
                if isinstance(last, Gtk.Label) and tuple(it for it in last.get_css_classes() if not it == "link") == tuple(it for it in w[0]["css_classes"] if not it == "link"): last.set_label(last.get_label() + "\n" + w[0]["label"])
                else:
                    last = Gtk.Label(**w[0], **self.args)
                    last.connect("activate-link", self.__class__.open_link)
                    Task.invoke(self.append, last)
            elif w:
                wa = Adw.WrapBox(**self.wargs)
                for i in w:
                    last = wa.get_last_child()
                    if isinstance(last, Gtk.Label) and tuple(it for it in last.get_css_classes() if not it == "link") == tuple(it for it in i["css_classes"] if not it == "link"): last.set_label(last.get_label().strip() + " " + i["label"])
                    else:
                        i["label"] += " "
                        last = Gtk.Label(**i, **self.args)
                        last.connect("activate-link", self.__class__.open_link)
                        wa.append(last)
                last.set_label(last.get_label().strip())
                last = wa
                Task.invoke(self.append, last)
            elif isinstance(last, Gtk.Label): last.set_label(last.get_label().strip() + "\n")
            else:
                last = Gtk.Label(**self.args)
                Task.invoke(self.append, last)
        for i in self:
            if isinstance(i, Adw.Spinner): Task.invoke(i.unparent)

    @staticmethod
    def open_link(label, uri):
        if not label.get_ancestor(Thread): return False
        uri = uri.strip()
        if uri.startswith(">>"):
            thread = label.get_ancestor(Thread)
            for i in thread.box:
                if "highlight" in i.get_css_classes():
                    i.remove_css_class("highlight")
                    if i.get_name() == uri.strip(">>"): return True
            i = next(iter(i for i in thread.box if i.get_name() == uri.strip(">>")), False)
            if not i and tuple(it for it in thread.total if it.get("ID", "") == uri.strip(">>")):
                while not i and thread.replies:
                    thread.load_replies(3)
                    i = next(iter(i for i in thread.box if i.get_name() == uri.strip(">>")), False)
            if i:
                if "highlight" in i.get_css_classes(): i.remove_css_class("highlight")
                else:
                    Task.invoke(i.add_css_class, "highlight")
                    Task.invoke(thread.get_child().scroll_to, i)
            return True

class ParseComment(HTMLParser):
    def __init__(self, comment):
        self.tags, self.current_css = [], []
        self.body = [[]]
        super().__init__()
        if comment: self.feed(comment.replace("<wbr>", "").strip("`"))

    def handle_starttag(self, tag, attrs):
        if tag == "br": self.body.append([])
        if tag == "s": self.current_css.append("spoiler")
        if tag in ("b", "strong"): self.tags.append("b")
        if tag == "em": self.tags.append("i")
        if tag == "code": self.current_css.append("code")
        if tag == "a": self.tags.append("a")
        if [i for i in attrs if i[0] == "class"]:  self.current_css.append([i[1] for i in attrs if i[0] == "class"][0].split(" "))

    def handle_endtag(self, tag):
        if tag == "br": return
        if self.current_css: self.current_css.remove(self.current_css[-1])
        self.tags = []

    def handle_data(self, data):
        url = "a" in self.tags or data.startswith("https://")
        if url and "a" in self.tags: self.tags.remove("a")
        if data.startswith(">>") and url:
            if not self.current_css: self.current_css.append([])
            self.current_css[-1].append("link")
        args = { "label": GLib.markup_escape_text(data).strip(), "css_classes": tuple(it for i in self.current_css for it in i) }
        if args["label"]:
            if url:
                args["label"] = f'<a href="{args["label"]}" class="link">{args["label"]}</a>'
            else:
                for i in self.tags:
                    args["label"] = f"<{i}>" + args["label"] + f"</{i}>"
        if args["label"]: self.body[-1].append(args)

class Reply(Comment):
    __gtype_name__ = "Reply"

    def __init__(self, o, s, full):
        Gtk.Box.__init__(self, name=str(o.get("ID", "0")), css_name=self.__gtype_name__.lower(), halign=Gtk.Align.START, orientation=Gtk.Orientation.VERTICAL)
        if full.index(o) == 0: Task.invoke(self.add_css_class, "op")
        name, country, country_name, _id, tripcode, comment = tuple(self.__class__.get_prop(o, i) for i in ("name", "country", "country_name", "poster_id", "trip", "comment"))
        t = []
        if _id: t.append(_id)
        if country: t.append(country_name)
        label = " ".join([GLib.DateTime.new_from_unix_utc(o.get("Created At", GLib.DateTime.new_now_utc().to_unix())).to_local().format("%x (%a) %T"), f"No.{self.get_name().rsplit('_', 1)[-1]}"])
        for i in full:
            if f"&gt;&gt;{self.get_name()}" in (self.__class__.get_prop(i, "comment") or ""):
                l = f"&gt;&gt;{i.get('ID', '0')}"
                label += f' <a href="{l}" class="link"><small>{l}</small></a>'
        label = Gtk.Label(selectable=True, xalign=0, halign=Gtk.Align.START, wrap=True, label=label, use_markup=True)
        label.connect("activate-link", Comment.open_link)
        box = Gtk.Box(css_name="header")
        for i in (Gtk.Label(selectable=True, xalign=0, halign=Gtk.Align.START, wrap=True, label=(f"<b>{name}</b> "  + (f"{country}" if country else "")).strip(), css_classes=("name",), tooltip_text=" ".join(t), use_markup=True), label): box.append(i)
        Task.invoke(self.prepend, box)
        medias = []
        if "media" in o and o["media"] or "filename" in o or "embed" in o: medias.append(o)
        if "extra_files" in o:
            for n, i in enumerate(o["extra_files"]):
                no = dict(o)
                no["no"] = f"{o['no']}-{n + 2}"
                no.update(i)
                medias.append(no)
        if len(medias) > 1:
            bottom = Adw.WrapBox(child_spacing=8, line_spacing=8)
            Task.invoke(self.append, bottom)
        else:
            bottom = self
        for i in medias:
            i["Board"] = s
            p = Post(i, parent=bottom)
            Task.invoke(p.set_tooltip_text, self.__class__.get_prop(i, "filename"))
        if comment: Task.invoke(Comment.__init__, self, comment, {"yalign": 0, "xalign": 0, "halign": Gtk.Align.START}, {})

    def get_prop(p, k):
        if k == "comment":
            if "comment_processed" in p: return (f"<b>{p['title']}</b><br>" if "title" in p and p["title"] else "") + p["comment_processed"]
            if "sub" in p or "com" in p: return (f"<b>{p['sub']}</b><br>" if "sub" in p else "") + (p["com"] if "com" in p else "")
        if k == "filename":
            if "media" in p and p["media"] and "media_filename" in p["media"]: return p["media"]["media_filename"]
            if "filename" in p and "ext" in p: return p["filename"] + p["ext"]
        if k == "poster_id":
            if "poster_hash" in p: return p["poster_hash"]
            if "id" in p: return p["id"]
        if k == "country" and "poster_country" in p: return p["poster_country"]
        if k == "country_name" and "poster_country_name" in p: return p["poster_country_name"]
        if k.lower().replace(" ", "_") in p: return p[k.lower().replace(" ", "_")]

class Thread(Gtk.ScrolledWindow):
    __gtype_name__ = "Thread"

    def __init__(self, q):
        self.total = q[3]
        self.replies = q[3][50 * (q[1] - 1):]
        self.board = q[2]
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        super().__init__(css_name=self.__gtype_name__.lower(), child=Gtk.Viewport(scroll_to_focus=False, child=self.box))
        self.connect("edge-reached", self.__class__.load_replies)
        Task.invoke(self.load_replies)

    def get_posts(self):
        posts = []
        for reply in self.box:
            for i in reply:
                if isinstance(i, Post): posts.append(i)
                else:
                    for it in i:
                        if isinstance(it, Post): posts.append(it)
        return posts

    def load_replies(self, p=None):
        if p != None and p != 3 or not self.replies: return
        r = tuple(self.replies)[:50]
        self.replies = tuple(i for i in self.replies if not i in r)
        for i in r: Task.invoke(self.box.append, Reply(i, self.board, self.total))
        if p == 3:
            if self.get_parent():
                self.get_parent().set_page(self.get_parent().get_page() + 1)
                Task.invoke(self.get_parent().sync)
        if self.get_parent(): Task.invoke(Toast, f"{self.get_parent().get_page()} of {total_pages(len(self.total), 50)}")

class Manga(Gtk.ScrolledWindow):
    __gtype_name__ = "Manga"

    def __iter__(self):
        for i in self.get_child().get_child().get_child(): yield i

    def __init__(self, q):
        clamp = Adw.Clamp(halign=Gtk.Align.CENTER, child=Gtk.Box(orientation=Gtk.Orientation.VERTICAL), unit=Adw.LengthUnit.PX)
        if isinstance(q["File URL"], str):
            f = Gio.File.new_for_uri(q["File URL"])
            self.pages = tuple(f"archive://{f.peek_path()}|{GLib.DIR_SEPARATOR_S}{i}" for i in sorted(zipfile.ZipFile(f.peek_path(), "r").namelist(), key=alphabetical_sort))
        else:
            self.pages = q["File URL"]
        for i in ("maximum-size", "tightening-threshold"): App.default.get_active_window().lookup_action("manga-width").bind_property("state", clamp, i, DEFAULT_BIND, unpack_bind)
        super().__init__(css_name=self.__gtype_name__.lower(), focusable=True, child=Gtk.Viewport(child=clamp, vscroll_policy=Gtk.ScrollablePolicy.NATURAL))
        Task.invoke(self.load_pages)
        self.connect("edge-reached", self.__class__.load_pages)
        self.get_vadjustment().connect("value-changed", self.sync_page)

    def get_posts(self): return tuple(i for i in self.get_child().get_child().get_child())

    def load_pages(self, p=3):
        if not p == 3: return
        count = 0
        pages = self.pages[self.q[1] - 1:] if p == 3 else self.pages[:self.q[1] - 1]
        w = None
        for i in pages:
            if tuple(it for it in self if it.get_name() == i): continue
            count += 1
            if count >= 10:
                self.sync_page(self.get_vadjustment())
                Toast(f"{self.q[1]} of {len(self.pages)}")
                return
            paintable = next((it for it in get_paintables() if it.uri == i), False)
            ww = Gtk.Picture(name=i, hexpand=True, vexpand=True)
            if paintable: ww.set_paintable(paintable)
            else: ww.set_paintable(Adw.SpinnerPaintable.new(self))
            if w: self.get_child().get_child().get_child().insert_child_after(ww, w)
            else:
                if p == 2: self.get_child().get_child().get_child().prepend(ww)
                else: self.get_child().get_child().get_child().append(ww)
            w = ww
            if not paintable:
                w.task = Post.start_task(w, i)

    def sync_page(self, adjustment):
        widget = self.pick(self.get_width() / 2, self.get_height() / 2, Gtk.PickFlags.DEFAULT)
        if isinstance(widget, Gtk.Picture) and widget.get_parent() == self.get_child().get_child().get_child():
            v = self.pages.index(widget.get_name()) + 1
            t = self.get_ancestor(Tab)
            if t and v != self.q[1]:
                self.q[1] = v
                t.set_current_query(self.q)
                t.get_root().search.page = v
                Task.invoke(Palette.set_colors, widget.get_paintable())

class Chapter(ListObject):
    __gtype_name__ = "Chapter"
    title = GObject.Property(type=str)
    subtitle = GObject.Property(type=str)
    url = GObject.Property(type=str)

    @staticmethod
    def setup(f, l):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, name="")
        box.bind_property("name", box, "sensitive", DEFAULT_BIND, bool_bind)
        for _ in range(2):
            label = Gtk.Label(vexpand=True, use_markup=True, single_line_mode=True, ellipsize=Pango.EllipsizeMode.END)
            label.bind_property("label", label, "visible", DEFAULT_BIND, bool_bind)
            box.append(label)
        l.set_child(box)

    @staticmethod
    def bind(f, l):
        l.binds = []
        box = l.get_child()
        l.binds.append(l.get_property("item").bind_property("url", box, "name", DEFAULT_BIND))
        l.binds.append(l.get_property("item").bind_property("title", box.get_first_child(), "label", DEFAULT_BIND))
        l.binds.append(l.get_property("item").bind_property("subtitle", box.get_last_child(), "label", DEFAULT_BIND))

    @staticmethod
    def unbind(f, l):
        if hasattr(l, "binds"):
            for i in l.binds: i.unbind()
            del l.binds

    @staticmethod
    def teardown(f, l): l.set_child(None)

class Chapters(Gtk.Overlay):
    __gtype_name__ = "Chapters"
    model = GObject.Property(type=List)

    def __init__(self, chapters=None, data=""):
        l = Gtk.ListView(single_click_activate=True, halign=Gtk.Align.CENTER, css_classes=("navigation-sidebar",), model=Gtk.NoSelection())
        sw = Gtk.ScrolledWindow(child=l)
        sw.connect("edge-reached", self.__class__.load_more)
        super().__init__(css_name=self.__gtype_name__.lower(), child=sw)
        self.count = data
        self.add_overlay(Adw.StatusPage(icon_name="edit-find-symbolic", title="No Results"))
        l.get_model().bind_property("n-items", self.get_last_child(), "visible", DEFAULT_BIND, invert_bool_bind)
        if not hasattr(Chapter, "factory"):
            factory = Chapter.factory = Gtk.SignalListItemFactory.new()
            factory.connect("setup", Chapter.setup)
            factory.connect("bind", Chapter.bind)
            factory.connect("unbind", Chapter.unbind)
            factory.connect("teardown", Chapter.teardown)
        l.connect("activate", self.__class__.activate)
        l.set_factory(Chapter.factory)
        self.bind_property("model", l.get_model(), "model", DEFAULT_BIND)
        self.model = List(Chapter, list=chapters if chapters else [])

    @staticmethod
    def load_more(sw, p=3):
        self = sw.get_parent()
        if not self: return
        if p == 3 and not self.get_parent().tab.get_loading():
            if getattr(self, "count", False): self.get_parent().load(next_page=True)

    def load_page(self, q=None, data=""):
        self.count = data
        for i in (q[3] if q else []):
            if "Chapters" in i: self.model.extend(i["Chapters"])

    @staticmethod
    def activate(listview, p): Tab.create(query=listview.get_model().get_item(p).url)

class Board(ListObject):
    __gtype_name__ = "Board"

    engines = List(Gtk.StringObject, unique="string", list=("Cardboard", "Danbooru", "Gelbooru", "Moebooru", "MangaDex", "4chan", "FoolFuuka", "vichan", "Pixiv", "Nitter", "Pinterest"), static=True)

    id = GObject.Property(type=int, nick="ID", default=0)

    @GObject.Property(type=str)
    def name(self): return getattr(self, "_name", "")

    @name.setter
    def name(self, value):
        old_name = self.name
        self._name = value
        if old_name:
            if not self in Boards.list.default.get_model(): return
            App.default.data.update(table=self.__class__.__gtype_name__ + "s", column="Name", value=self.name, conditions="Name = ?", conds=(old_name,))
            App.default.data.update(table="Posts", column="Board", value=self.name, conditions="Board = ?", conds=(old_name,))
            prev = App.default.data_folder.get_child(old_name)
            if prev.query_exists(): prev.move(App.default.data_folder.get_child(self.name), Gio.FileCopyFlags.NONE)
            for t in Tab.get_all():
                for i in t.history:
                    if i[2] == old_name:
                        i[2] = self.name
                        t.update_title()
                if hasattr(t.get_child(), "q") and t.get_child().q[2] == old_name:
                    t.get_child().q[2] = self.name
                    t.update_title()
                if hasattr(t.get_child(), "board") and t.get_child().board == old_name:
                    t.get_child().board = self.name
                    t.update_title()
                if hasattr(t.get_child(), "get_posts"):
                    for i in t.get_child().get_posts():
                        if isinstance(i, Post) and i.board == old_name:
                            i.board = self.name
                    t.update_title()
            Tab.idle_save_all()
            Task.invoke(Boards.list.default.get_model().do_dict)

    engine = GObject.Property(type=str, default="Cardboard")
    url = GObject.Property(type=str)
    append_to_search = GObject.Property(type=str, nick="Append to Search")
    search_autocomplete = GObject.Property(type=bool, default=True)
    launch_sources = GObject.Property(type=bool, default=False)
    download_favorites = GObject.Property(type=bool, default=False)
    download_thumbnails = GObject.Property(type=bool, default=False)

    @staticmethod
    def changed(self, p):
        if getattr(self, "changing", False): return
        if not self in Boards.list.default.get_model(): return
        name = p.get_name().replace("-", "_")
        v = getattr(self, name, None)
        p = p.get_nick() or name.title().replace("_", " ")
        App.default.data.update(table=self.__class__.__gtype_name__ + "s", column=p, value=v, conditions="Name = ?", conds=(self.name,))

    @staticmethod
    def setup(f, l): l.set_child(Gtk.Label(xalign=0))

    @staticmethod
    def bind(f, l):
        if not l.get_child(): return
        l.get_child().bindings = [l.get_property("item").bind_property("name", l.get_child(), "label", DEFAULT_BIND)]

    @staticmethod
    def unbind(f, l):
        for i in getattr(l.get_child(), "bindings", []): i.unbind()
        if hasattr(l.get_child(), "bindings"): del l.get_child().bindings

    @staticmethod
    def teardown(f, l): l.set_child(None)

    def new(*_):
        name = unique_name("New Board", Boards.list.default.get_model())
        App.default.data.new(table="Boards", values=(name,), names=("Name",))
        Boards.list.default.get_model().add(App.default.data.read(table="Boards", conds=(name,), conditions="Name = ?", return_dict=True))

    factory = Gtk.SignalListItemFactory.new()
    factory.connect("setup", setup)
    factory.connect("bind", bind)
    factory.connect("unbind", unbind)
    factory.connect("teardown", teardown)

class BoardsMeta(type(Gtk.Popover)):
    def __iter__(*_):
        for i in range(len(Boards.list.default.get_model())): yield Boards.list.default.get_item(i)

class Boards(Gtk.Popover, metaclass=BoardsMeta):
    __gtype_name__ = "Boards"

    model = GObject.Property(type=Gtk.SingleSelection)
    list = GObject.Property(type=Gtk.SortListModel, default=Gtk.SortListModel(sorter=Gtk.NumericSorter(expression=Gtk.PropertyExpression.new(Board, None, "id")), model=List(Board, unique="name", static=True)))

    def __init__(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        super().__init__(autohide=False, has_arrow=False, child=box)
        self.model = Gtk.SingleSelection(autoselect=True, can_unselect=False)
        self.bind_property("list", self.model, "model", DEFAULT_BIND)
        listview = Gtk.ListView(model=self.model, factory=Board.factory)
        listview.set_css_classes(["navigation-sidebar"])
        listview.connect("activate", self.__class__.row_activate)
        box.append(Gtk.ScrolledWindow(propagate_natural_height=True, propagate_natural_width=True, child=listview))
        box.append(Gtk.Separator())
        self.list.bind_property("n-items", box.get_last_child(), "visible", DEFAULT_BIND, bool_bind)
        box.append(Button(callback=Board.new, label="Add New Board", css_classes=["flat"]))
        box.get_last_child().get_first_child().set_xalign(0)
        self.add_css_class(self.__gtype_name__.lower())

    @staticmethod
    def row_activate(l, n):
        if not isinstance(n, int): return
        self = l.get_ancestor(Boards)
        if not self: return
        self.popdown()
        item = l.get_model().get_item(n)
        page = GroupsPage()
        group = Adw.PreferencesGroup()
        page.add(group)
        l = []
        l.append(Adw.EntryRow(title="Name", text=item.name, show_apply_button=True))
        l[-1].connect("apply", self.__class__.change_name)
        for i in ("URL", "Append to Search"):
            l.append(Adw.EntryRow(title=i))
            if i == "URL": item.bind_property("engine", l[-1], "title", DEFAULT_BIND, self.__class__.url_title_bind)
            else: item.bind_property("engine", l[-1], "title", DEFAULT_BIND, self.__class__.append_to_search_title_bind)
            item.bind_property(i.lower().replace(" ", "-"), l[-1], "text", SYNC_BIND)
        for i in ("Search Autocomplete", "Launch Sources", "Download Favorites", "Download Thumbnails"):
            l.append(Adw.SwitchRow(title=i))
            item.bind_property(i.lower().replace(" ", "-"), l[-1], "active", SYNC_BIND)
        l.append(Adw.ComboRow(title="Engine", model=Board.engines))
        item.bind_property("engine", l[-1], "selected", SYNC_BIND, self.__class__.engine_bind, self.__class__.engine_bind)
        for i in l: group.add(i)
        header = Adw.HeaderBar()
        header.pack_end(PopupDialogButton())
        header.pack_end(Button(icon_name="user-trash", tooltip_text="Delete Search", callback=self.__class__.prompt_delete))
        edit = PopupDialog(content=Adw.ToolbarView(content=page), content_height=505, content_width=500)
        edit.get_content().add_top_bar(header)
        item.bind_property("name", edit, "title", DEFAULT_BIND)
        edit.present(Window.current)

    @staticmethod
    def url_title_bind(b, v):
        if v in ("Cardboard", "MangaDex", "Pixiv", "Pinterest"): return "Default Search"
        if v == "Nitter": return "Instance (leave empty for auto)"
        if v == "4chan": return "4chan Board Name"
        if v in ("vichan", "FoolFuuka"): return "Board URL"
        if v in ("Danbooru", "Gelbooru", "Moebooru"): return "Booru URL"
        return "URL"

    @staticmethod
    def append_to_search_title_bind(b, v):
        if v == "Gelbooru": return "Append to Search (usually user_id and api_key required)"
        return "Append to Search"

    @staticmethod
    def engine_bind(b, v):
        target = b.get_property("target")
        model = target if isinstance(target, Gio.ListModel) else target.get_model() if hasattr(target, "get_model") else False
        if isinstance(v, int): return model[v].get_string()
        return model.index(v)

    @staticmethod
    def do_delete(d):
        App.default.data.delete(table="Boards", conditions="Name = ?", conds=(d.dialog.get_title(),))
        Boards.list.default.get_model().remove(d.dialog.get_title())
        if d.dialog: d.dialog.close()
        del d.dialog

    @staticmethod
    def prompt_heading(b, v): return f"Delete {v}?"

    @staticmethod
    def prompt_delete(b):
        if len(Boards.list.default.get_model()) == 1: return Toast("At least one board is required")
        delete = Prompt(callback=Boards.do_delete, appearance=Adw.ResponseAppearance.DESTRUCTIVE)
        delete.dialog = PostEditor.get_self(b)
        delete.dialog.bind_property("title", delete, "heading", DEFAULT_BIND, Boards.prompt_heading)
        delete.present(Window.current)

    @staticmethod
    def change_name(w, p=None):
        d = w.get_ancestor(Adw.Dialog)
        if not d: return
        t = w.get_text()
        if not t: return Toast("Name can't be empty")
        if t in Boards.list.default.get_model(): return Toast(f"{t} already exists")
        Boards.list.default.get_model()[d.get_title()].name = t

    def set_selected(self, name):
        l = [self.model.get_item(i).name for i in range(self.model.get_n_items())]
        self.model.select_item(l.index(name) if name and name in l else Gtk.INVALID_LIST_POSITION, True)

    def get_selected(self): return self.model.get_selected_item()

class Suggestion(ListObject):
    __gtype_name__ = "Suggestion"
    label = GObject.Property(type=str)
    value = GObject.Property(type=str)

class Search(Gtk.Box):
    __gtype_name__ = "Search"
    page = GObject.Property(type=int, minimum=1, default=1)
    locked = GObject.Property(type=bool, default=False)
    autocomplete = GObject.Property(type=Autocomplete)
    boards = GObject.Property(type=Boards)
    query = GObject.Property(type=Gtk.Text)
    completer = Gio.FilenameCompleter()

    def __init__(self):
        super().__init__(css_name="search")
        self.boards = Boards()
        self.query = Gtk.Text(placeholder_text="Search", css_name="query", xalign=0.50, hexpand=True)
        page_query = Gtk.Text(css_classes=("dimmed",), propagate_text_width=True)
        for i in (self.query, page_query): self.append(i)
        self.prepend(Gtk.Picture(opacity=0, paintable=Gtk.WidgetPaintable.new(page_query)))
        self.bind_property("page", page_query, "text", SYNC_BIND, str_bind, self.__class__.page_bind)
        self.autocomplete = Autocomplete(self.query, model=List(Suggestion), bind=self.__class__.bind, setup=self.__class__.setup, text_activate=self.__class__.text_activate, row_activate=self.__class__.row_activate, select=self.__class__.select, complete=self.__class__.complete)

    @staticmethod
    def setup(f, l): l.set_child(Gtk.Label(use_markup=True, xalign=0))

    @staticmethod
    def bind(f, l):
        l.get_child().bindings = [l.get_property("item").bind_property("label", l.get_child(), "label", DEFAULT_BIND)]

    @staticmethod
    def text_activate(text, autocomplete, s):
        self = text.get_root()
        if not self: return
        if Gdk.ModifierType.SHIFT_MASK in s:
            Tab.create(query=self.search.get_text(), page=self.search.page, board=self.search.boards.get_selected().name)
            return True
        else:
            if self.search.boards: self.search.boards.popdown()
            t = self.stack.get_visible_child().get_selected_page()
            if not t: return
            t = t.get_child()
            if hasattr(t.get_child(), "q"): del t.get_child().q
            t.load(query=self.search.get_text(), page=self.search.page, board=self.search.boards.get_selected().name)
            return True

    @staticmethod
    def row_activate(text, autocomplete, item):
        self = text.get_ancestor(Search)
        t = self.get_current_word(item.value)[0] if item else ""
        if not item or not t or self.get_current_word() == item.value:
            autocomplete.popdown()
            autocomplete.model.replace()
            return True
        autocomplete.set_text(t)
        return True

    @staticmethod
    def select(text, autocomplete, item): return autocomplete.set_text(*text.get_ancestor(Search).get_current_word(item.value))

    @staticmethod
    def complete(autocomplete, text):
        self = text.get_ancestor(Search)
        self.page = 1
        if not text.get_text() or not self.boards.get_selected().search_autocomplete: return
        q = self.get_current_word()
        if q.startswith(("http://", "https://")): return
        elif q.startswith(("/", "file://")):
            q = uri_decode(q) if q.startswith("file://") else q
            self.do_complete([{"label": basename(i), "value": uri_encode(i.rstrip("/") or "/")} for i in Search.completer.get_completions(q)])
        elif q.startswith(("regex", "-regex")): self.do_complete([{"label": PostData.prop_get_title(i), "value": (("regex" if q.startswith("r") else "-regex") + "_" + i + ":")} for i in PostData.default_names])
        elif q.startswith(("board:", "-board:")): self.do_complete([{"label": i.name, "value": ("board:" if q.startswith("b") else "-board:") + i.name.replace(" ", "_")} for i in Boards])
        else:
            self.add_css_class("searching")
            Task(self.do_complete, q).start()

    def do_complete(self, q):
        if isinstance(q, str) and q:
            try:
                q = Online.Request(f"https://danbooru.donmai.us/autocomplete.json?search[query]={GLib.Uri.escape_string(q)}&search[type]=tag_query&limit=15", headers={"User-Agent": "Cardboard"})
                q = json(q.decode()) if q else []
            except Exception as e:
                Task.invoke(Toast, f"Autocomplete error: {e}")
                q = []
        else:
            q = []
        l = [Suggestion(label=f"{GLib.markup_escape_text(i['antecedent'])} → <b>{GLib.markup_escape_text(i['label'])}</b>" if "antecedent" in i else GLib.markup_escape_text(i["label"]), value=i["value"]) for i in (q or [])]
        Task.invoke(self.remove_css_class, "searching")
        Task.invoke(self.autocomplete.model.replace, l)
        Task.invoke(self.autocomplete.listview.get_model().unselect_all)

    def get_text(self): return self.query.get_text()

    def set_text(self, t=""): self.autocomplete.set_text(t if isinstance(t, str) else "")

    @staticmethod
    def page_bind(b, v): return min(int(v), GLib.MAXINT32) if v.isdigit() else 1

    def get_current_word(self, v=None):
        q = self.get_text().split(" ")
        length, closest_index = 0, -1
        for i, word in enumerate(i for i in q):
            length += len(word) + 1
            if length > self.query.get_position():
                closest_index = i
                if i > 0 and (self.query.get_position() - (length - len(word) - 1)) < (length - self.query.get_position()):
                    closest_index = i - 1
                break
        if v:
            pw = q[closest_index]
            q[closest_index] = v
            return (" ".join(q), length - len(pw) + len(v) - 1)
        return q[closest_index]

class Pixiv:
    headers = {"App-OS": "ios", "App-OS-Version": "16.7.2", "App-Version": "7.19.1", "User-Agent": "PixivIOSApp/7.19.1 (iOS 16.7.2; iPhone12,8)", "Referer": "https://app-api.pixiv.net/"}
    @staticmethod
    def monitor_code(s, a, b, w):
        if "code=" in b.get_uri():
            Online.add_cookie(name="code", value=b.get_uri().split("code=")[-1].split("&")[0], domain="pixiv.net", expires=GLib.DateTime.new_now_utc().add_seconds(30))
            Task.invoke(Pixiv.get_auth, w.tab, w=w)

    @staticmethod
    def get_auth(tab, w=None):
        code, refresh_token = [Online.get_cookie(name=i, domain="pixiv.net") for i in ("code", "refresh_token")]
        if not w and refresh_token: return refresh_token
        elif w:
            multipart = {"client_id": "MOBrBDS8blbauoSck0ZfDbtuzpyT", "client_secret": "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"}
            if w: multipart.update({"grant_type": "authorization_code", "code": code, "code_verifier" : w.code_verifier, "include_policy": "true", "redirect_uri" : "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback",})
            else: multipart.update({"grant_type": "refresh_token", "refresh_token": refresh_token, "get_secure_url": "1", "include_policy": "true"})
            ti = GLib.DateTime.new_now_utc().format("%Y-%m-%dT%H:%M:%S+00:00")
            headers = {**Pixiv.headers, "X-Client-Time": ti, "X-Client-Hash": (md5 := GLib.Checksum.new(GLib.ChecksumType.MD5), md5.update((ti + "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c").encode()), md5.get_string())[-1]}
            res = json(Online.MultipartRequest(f"https://oauth.secure.pixiv.net/auth/token", fields=multipart, headers=headers).decode())
            if "access_token" in res: Online.add_cookie(name="refresh_token", value=res["access_token"], domain="pixiv.net", expires=GLib.DateTime.new_now_utc().add_hours(1).to_unix())
            Task.invoke(w.close)
            Task.invoke(tab.load)
        else: Task.invoke(Pixiv.login, tab)

    @staticmethod
    def login(tab):
        from hashlib import sha256
        from base64 import urlsafe_b64encode
        code_verifier = urlsafe_b64encode(urandom(32))[:-1]
        code_challenge = urlsafe_b64encode(bytes.fromhex(sha256(code_verifier).hexdigest()))[:-1].decode("ascii")
        Online.Intervention(f"https://app-api.pixiv.net/web/v1/login?code_challenge={code_challenge}&code_challenge_method=S256&client=pixiv-android", function=Pixiv.setup, function_data=(tab, code_verifier.decode("ascii"), code_challenge))

    @staticmethod
    def setup(w, d):
        w.view.connect("resource-load-started", Pixiv.monitor_code, w)
        w.tab, w.code_verifier, w.code_challenge = d
        w.set_title("Pixiv Login")
        Task.invoke(Toast, "Pixiv authentication required...")

class Extractor(GObject.Object):
    __gtype_name__ = "Extractor"

    tab = GObject.Property(type=Tab)
    paintable = GObject.Property(type=Gdk.Paintable)
    text = GObject.Property(type=str)

    current_url = GObject.Property(type=str)
    current_query = GObject.Property(type=str)
    current_headers = GObject.Property(type=object)
    current_catalog = GObject.Property(type=object)

    obj = GObject.Property(type=object)
    next_page = GObject.Property(type=object)
    queries = GObject.Property(type=object)
    page = GObject.Property(type=int)
    board = GObject.Property(type=str)
    engine = GObject.Property(type=str)
    catalog = GObject.Property(type=object)
    count = GObject.Property(type=object)

    is_str = GObject.Property(type=bool, default=False)

    def __init__(self, tab):
        super().__init__()
        self.catalog = []
        self.tab = tab
        self.next_page = self.tab.next_page
        self.queries, self.page, self.board = self.tab.get_current_query()[:-1]
        self.is_str = type(self.queries) == str
        Task(self.do_fetch).start()

    def response_to_object(self):
        t, tt = "", False
        try:
            t = Online.Request(self.current_url, self.current_headers)
            try:
                tt = t.decode().strip()
                if not tt:
                    Online.Intervention(self.current_url)
                    return
                self.text = tt
                if tt.startswith(("<?xml", "<!DOCTYPE html")): return
                self.obj = json(tt)
                return
            except Exception as e:
                if tt:
                    self.text = tt
                    return
                try:
                    self.paintable = PaintableTask.data_to_paintable(t, self.current_url)
                    return
                except Exception as e:
                    print(self.current_url, e)
                    Online.Intervention(self.current_url)
                return
        except Exception as e:
            print(self.current_url, e)
            Online.Intervention(self.current_url)
            return

    def do_fetch(self):
        final_queries = []
        self.queries = [i for i in self.queries.split(" + ") if i] if self.is_str else self.queries
        if not self.queries:
            self.queries = [""]
        for query in self.queries:
            self.current_query = query
            self.obj = None
            self.text = self.current_url = ""
            self.current_catalog = []
            self.current_headers = {}
            if not self.is_str:
                self.engine = getattr(Boards.list.default.get_model()[self.board], "engine", "Cardboard")
                continue
            if self.next_page and isinstance(self.tab.get_child().count, str) and self.tab.get_child().count == "end":
                final_queries.append(self.current_query)
                self.page -= 1
                continue
            self.query_to_url()
            if self.next_page:
                if isinstance(self.tab.get_child().count, str):
                    self.current_url = self.tab.get_child().count
            final_queries.append(self.current_query)
            if any(i in self.current_url for i in ("mangadex.org", ".donmai.us")): self.current_headers.update({"User-Agent": "Cardboard"})
            if "pinterest.com" in self.current_url:
                if not Online.get_cookie(domain="pinterest.com", name="csrftoken"): Online.add_cookie(name="csrftoken", value=urandom(16).hex(), domain=".pinterest.com")
                self.current_headers.update(PINTEREST_HEADERS)
            if self.engine == "Nitter": self.current_headers.update(NITTER_HEADERS)
            if "pixiv.net" in self.current_url:
                auth = Pixiv.get_auth(self.tab)
                if not auth: continue
                self.current_headers.update({**Pixiv.headers, "Authorization": f"Bearer {auth}"})
            if "/api/v1" in self.current_url: self.current_headers.update({"Accept": "text/css"})
            if not (self.text or self.obj) and self.current_url and is_online(self.current_url) and not self.current_catalog: self.response_to_object()
            if "youtube.com" in self.current_url and is_online(self.current_url): self.current_catalog.append({"ID": self.current_url.replace("www.", "").replace("be.com/watch?v=", ".be/").split("?")[0].rsplit("/", 1)[-1], "Source": self.current_url.replace("www.", "").replace("be.com/watch?v=", ".be/").split("?")[0], "File URL": self.current_url.replace("www.", "").replace("be.com/watch?v=", ".be/").split("?")[0].replace("youtu.be", "img.youtube.com/vi").split("&", 1)[0] + "/maxresdefault.jpg"})
            elif (self.text or self.obj or self.paintable):
                if self.text: self.from_str()
                if self.paintable: self.current_catalog.append({"File URL": self.current_url})
                if self.obj: self.from_json()
            elif self.current_query.startswith(("archive://", "file://", "http://", "https://")) and not self.current_catalog:
                if self.current_query.startswith("file://"):
                    root = uri_decode(uri_relative_encode(self.current_query))
                    if exists(root):
                        if is_dir(root):
                            for r, d, f in walk(root): self.current_catalog.extend([{"File URL": Path(r.split(App.default.data_folder.get_path(), 1)[-1], i).lstrip("/") if r.startswith(App.default.data_folder.get_path()) else Path(r, i)} for i in sorted(f, key=alphabetical_sort) if Gio.content_type_guess(i)[0].startswith(("video", "audio", "image"))])
                    else: Task.invoke(Toast, f"{root} doesn't exist!")
                if not self.current_catalog: self.current_catalog.append({"File URL": self.current_query})
            elif self.engine == "Cardboard": self.cardboard()
            if "/_/api/chan/" in self.current_url:
                self.count = self.current_url.split("page=", 1)[0] + f"page={self.page + 1}" + (("&" + self.current_url.split("page=", 1)[-1].split("&", 1)[-1]) if "&" in self.current_url.split("page=", 1)[-1] else "")
            if isinstance(self.current_catalog, dict):
                self.current_catalog = [self.current_catalog]
            if self.current_query and not self.current_query.startswith(("http://", "archive://", "file://", "https://")) and not is_thread(query, self.engine) and self.engine in ("4chan", "vichan", "FoolFuuka"):
                for i in [i for i in self.current_catalog]:
                    co = Reply.get_prop(i, "comment")
                    if co and not self.current_query.lower() in co.lower(): self.current_catalog.remove(i)
            for i in self.current_catalog:
                if "File URL" in i and "files.catbox.moe" in i["File URL"]: i.setdefault("ID", "catbox_" + i["File URL"].split(".moe/", 1)[-1].strip("/").rsplit(".", 1)[0])
            self.catalog.extend(self.current_catalog)
        if self.count == None:
            self.count = (len(self.catalog), len(self.catalog))
        if self.is_str and len(self.queries) > 1: self.catalog.sort(key=id_sort, reverse=True)
        self.tab.set_current_query([" + ".join([i for i in final_queries if i]) if self.is_str else self.queries, self.page, self.board, self.catalog])
        Task.invoke(self.tab.content, self.tab.get_current_query(), self.engine, self.count, self.paintable, self.next_page)
        for i in self.list_properties():
            if i.name == "page": setattr(self, i.name, 0)
            else: setattr(self, i.name.replace("-", "_"), None)

    def from_str(self):
        if "challenge-error-text" in self.text or "This website is running Anubis" in self.text:
            Task.invoke(Online.Intervention, self.current_url, self.text)
            return
        elif "https://ogp.me/ns" in self.text and self.current_url.rsplit("/", 1)[-1].rsplit("?", 1)[0].isdigit() and "/user/" in self.current_url:
            self.current_headers.update({"Accept": "text/css"})
            start, rest = self.current_url.split("://", 1)[-1].split("/", 1)
            self.current_url = "https://" + start.strip("/") + "/api/v1/" + rest.strip("/").split("?", 1)[0]
            if not "post" in self.current_url:
                self.current_url += "/posts?o=" + str((self.page - 1) * 50)
            self.response_to_object()
        elif "Running Moebooru" in self.text and not ".xml" in self.current_url:
            self.engine = "Moebooru"
            self.url_from_url(True)
            self.response_to_object()
        elif "new Danbooru.Notice(null)" in self.text and not ".json" in self.current_url:
            self.engine = "Danbooru"
            self.url_from_url(True)
            self.response_to_object()
        elif 'content="FoolFuuka 2.2.0"' in self.text and not "/_/api/chan" in self.current_url:
            self.engine = "FoolFuuka"
            self.url_from_url(True)
            self.response_to_object()
        elif "vichan.net/" in self.text and not ".json" in self.current_url:
            self.engine = "vichan"
            self.url_from_url(True)
            self.response_to_object()
        elif "404" in self.text and "What you are looking for is not here." in self.text or "/official/images/404.png" in self.text and "Click me to go home" in self.text:
            Task.invoke(Toast, f"{u} returned 404")
            return
        if 'id="chapter-images"' in self.text:
            l = []
            for i in self.text.split("<img"):
                a = get_attribute(i, "src", default="").split("\"", 1)[0]
                if a: l.append(a)
            if l: self.current_catalog.append({"File URL": l, "Source": self.current_query})
        if "a href=\"/chapters/" in self.text and "/series/" in self.current_url and self.current_url.endswith("/full-chapter-list"):
            self.current_catalog = {"Chapters": [{"Title": i.split("</span>", 1)[0], "URL": self.current_url.split("/series/", 1)[0] + "/chapters/" + i.split("last_read_chapter === '", 1)[-1].split("'", 1)[0]} for i in self.text.split("<span class=\"\">")[1:]]}
            self.count = ""
        if self.text.startswith("<rss xml"):
            if "href=\"https://weebcentral" in self.text:
                self.current_catalog = {"Chapters": [m.groupdict() for m in ITEM_REGEX.finditer(self.text)]}
                main_title = self.text.split("</title>", 1)[0].split("<title>", 1)[-1]
                for i in self.current_catalog["Chapters"]:
                    i["Title"] = i["Title"].split(main_title, 1)[-1]
                self.count = ""
            head = ""
        elif self.text.startswith("<?xml"):
            if "count=" in self.text:
                self.count = (100, int(get_attribute(self.text, "count", default=0)))
            for m in POST_REGEX.finditer(self.text):
                attrs = {}
                for a, dq, sq, unq in ATTR_REGEX.findall(m.group(1) or ""):
                    attrs[a] = dq or sq or unq or ""
                i = {"Tags": []}
                if "tags" in attrs: i["Tags"].extend(attrs["tags"].split(" "))
                if "file_url" in attrs: i.setdefault("File URL", attrs["file_url"])
                if "source" in attrs: i.setdefault("Source", attrs["source"])
                if attrs.get("created_at", "").isdigit(): i.setdefault("Created At", int(attrs["created_at"]))
                if "rating" in attrs: i["Tags"].append(attrs["rating"])
                if attrs.get("parent_id", 0): i["Tags"].append(f"parent:{attrs['parent_id']}")
                if "id" in attrs:
                    i.setdefault("ID", attrs["id"])
                    if attrs.get("has_children", False): i["Tags"].append(f"parent:{attrs['id']}")
                self.current_catalog.append(i)
            head = ""
        else:
            head = self.text.split("</head>", 1)[0]
        if "site_name" in head and get_attribute(head.split("site_name", 1)[-1], "content") == "Nitter":
            global NITTER_INSTANCE
            if "Instance has no auth tokens, or is fully rate limited." in self.text:
                Task.invoke(Toast, "Nitter instance is rate limited")
                NITTER_SKIP.append(NITTER_INSTANCE)
                NITTER_INSTANCE = False
                return
            if "Search disabled" in self.text:
                Task.invoke(Toast, "Nitter instance has search disabled")
                NITTER_SKIP.append(NITTER_INSTANCE)
                NITTER_INSTANCE = False
                return
            self.count = (self.current_url.split("?", 1)[0] + get_attribute(self.text.split("show-more", 1)[-1].split("<a", 1)[-1], "href")) if '<div class="show-more">' in self.text else "end"
            if "timeline-item" in self.text:
                prefix = "" if getattr(Boards.list.default.get_model()[self.board], "engine", "") == "Nitter" else "nitter_"
                for i in self.text.split("timeline-item ")[1:]:
                    if not "attachment" in i: continue
                    user = get_attribute(i, "data-username")
                    _id = get_attribute(i.split("tweet-date", 1)[-1], "href").rsplit("/", 1)[-1].split("#")[0]
                    tags = []
                    body = i.split("media-body", 1)[-1].split(">", 1)[-1].split("</div>")[0]
                    if "#" in body:
                        for it in body.split("#")[1:]: tags.append(it.split(">", 1)[0].split("<", 1)[0])
                    body = "".join([it.split(">", 1)[-1] for it in body.split("<")])
                    for n, it in enumerate(i.split("attachment\">")[1:]):
                        it = it.split("</div>", 1)[0]
                        h = get_attribute(it, "href")
                        s = get_attribute(it, "src")
                        file = ""
                        if h.startswith(("https://pbs.twimg", "https://video.twimg")):
                            file = h
                        elif h and "video.twimg" in it:
                            file = "https://video." + h.split("video.", 1)[-1].replace("%2F", "/")
                        elif h and "href" in it:
                            file = "https://pbs.twimg.com/media/" + h.split("%2F")[-1]
                        elif s:
                            file = s.replace("/pic/", "https://").replace("%2F", "/").split("?", 1)[0]
                        self.current_catalog.append({"ID": f"{prefix}{_id}{('_' + str(n)) if n > 0 else ''}", "Tags": tags, "Notes": body.strip(), "Source": f"https://x.com/{user}/status/{_id}", "File URL": file.split("%", 1)[0]})
        else:
            for i in ("og:video:secure_url", "og:image:secure_url", "og:image"):
                if i in head:
                    p = {"File URL": get_attribute(head.split(i, 1)[-1], "content").replace(",resize:640x,quality:90x75", ""), "Source": self.current_url.replace("#comments", "")}
                    if "https://media" in p["File URL"] and ".tenor.com/" in p["File URL"]:
                        p["ID"] = "tenor_" + p["File URL"].rsplit("/", 1)[0].rsplit("/", 1)[-1]
                    elif "ifunny.co" in self.current_url:
                        p["ID"] = "ifunny_" +  p["Source"].rsplit("/", 1)[-1].rsplit("-", 1)[-1]
                        if "b7a_" in self.text:
                            p["Tags"] = [i.split("</span", 1)[0].strip("\">#") for i in self.text.split("b7a_")[1:]]
                    elif "memedroid.com/memes/detail/" in self.current_url:
                        p["ID"] = self.current_url.split("://", 1)[-1].split("www.", 1)[-1].replace(".com/memes/detail/", "_").split("/", 1)[0]
                    self.current_catalog.append(p)
                    break
            if "og:title" in head:
                for i in self.current_catalog: i.setdefault("Notes", get_attribute(head.split("og:title", 1)[-1], "content").replace(" on DeviantArt", "").replace("- iFunny", "").strip())
            elif "<title>" in head:
                for i in self.current_catalog: i.setdefault("Notes", head.split("<title>", 1)[-1].split("</title>")[0].replace(" on DeviantArt", "").replace("- iFunny", "").strip())
            if "keywords" in head:
                for i in self.current_catalog:
                    i.setdefault("Tags", [])
                    i["Tags"].extend([it.replace(" ", "_").strip("_") for it in get_attribute(head.split("keywords", 1)[-1], "content").split(",")])
            if "<h5>Options</h5>" in self.text:
                t = self.text.split("<h5>Options</h5>", 1)[-1].split("Original image", 1)[0].rsplit("href=\"", 1)[-1].split("\"", 1)[0]
                if is_online(t):
                    p = {"File URL": t, "Source": self.current_query, "Tags": []}
                    if "<ul id=\"tag-sidebar\">" in self.text:
                        for i in self.text.split("<ul id=\"tag-sidebar\">", 1)[-1].split("post&amp;s=list&amp;tags=")[1:]:
                            p["Tags"].append(html_unescape(GLib.Uri.unescape_string(i.split("\"", 1)[0])))
                            if "</li></ul>" in i: break
                    if "<h5>Statistics</h5>" in self.text:
                        stats = self.text.split("<h5>Statistics</h5>", 1)[-1]
                        if "Id: " in stats:
                            p["ID"] = self.current_query.split("://", 1)[-1].split("/", 1)[0] + "_" + stats.split("Id: ", 1)[-1].split("<", 1)[0]
                        if "Source: " in stats:
                            s = stats.split("Source: ", 1)[-1]
                            if s.startswith("<a href=\""):
                                p["Source"] = html_unescape(s.split("href=\"", 1)[-1].split("\"", 1)[0])
                            else:
                                p["Source"] = html_unescape(s.split("</li>", 1)[0])
                        if "Rating: " in stats: p["Tags"].append(stats.split("Rating: ", 1)[-1][:1].lower())
                        try:
                            date, time = stats.split("Posted: ", 1)[-1].split("<", 1)[0].split(" ")
                            args = date.split("-") + time.split(":")
                            if all(i.isdigit() for i in args):
                                args = [int(i) for i in args]
                                p["Created At"] = GLib.DateTime.new(GLib.TimeZone.new_local(), *args).to_utc().to_unix()
                        except: pass
                    self.current_catalog.append(p)

    def from_json(self):
        if type(self.obj) == dict:
            if "pinterest.com/resource/" in self.current_url:
                if not "resource_response" in self.obj: return
                if not "data" in self.obj["resource_response"]: return
                if "bookmarks" in self.obj["resource"]["options"]:
                    if self.obj["resource"]["options"]["bookmarks"][0] == "-end-":
                        self.count = "end"
                    else:
                        self.count = f"{self.current_url.split('data=', 1)[0]}data={json_string({'options': self.obj['resource']['options']})}&source_url="
                        if self.next_page and json(self.current_url.split("data=", 1)[-1].rsplit("&source_url=", 1)[0])["options"]["bookmarks"] == self.obj["resource"]["options"]["bookmarks"]:
                            self.count = "end"
                self.obj = (self.obj["resource_response"]["data"] or [])
                if isinstance(self.obj, dict):
                    if "results" in self.obj:
                        self.obj = self.obj["results"]
                    else:
                        self.obj = [self.obj]
                prefix = "" if getattr(Boards.list.default.get_model()[self.board], "engine", "") == "Pinterest" else "pinterest_"
                for i in self.obj:
                    if "images" in i:
                        tags = []
                        notes = i["seo_title"] if "seo_title" in i else ""
                        if i.get("pin_join", {}):
                            if not "id" in i and (i.get("pin_join", {}).get("canonical_pin", {}) or {}).get("id", False):
                                i["id"] = i["pin_join"]["canonical_pin"]["id"]
                            for it in i["pin_join"]["visual_annotation"]: tags.append(it.replace(" ", "-").lower())
                        if "board" in i: tags.extend([i["board"]["name"].replace(" ", "-").lower(), f"https://pinterest.com{i['board']['url'].lower()}"])
                        self.current_catalog.append({"ID": prefix + i["id"], "Tags": tags, "Notes": notes.strip(), "Source": f"https://pinterest.com/pin/{i['id']}", "File URL": i["images"]["orig"]["url"]})
                self.obj = {}
            if self.current_url.startswith("https://www.zerochan.net/") and self.current_url.split("/")[-1].split("?")[0].isdigit(): self.current_catalog.append({"File URL": self.obj["full"], "Source": self.obj["source"], "Tags": self.obj["tags"]})

            if "artstation.com/projects/" in self.current_url:
                for i in self.obj["assets"]:
                    file_url = i["image_url"]
                    for it in ("/small/", "/large/", "/medium/"):
                        file_url = file_url.replace(it, "/4k/")
                    self.current_catalog.append({"File URL": file_url.split("?")[0], "Source": self.current_query, "Created At": GLib.DateTime.new_from_iso8601(self.obj["created_at"]).to_utc().to_unix(), "Tags": self.obj["tags"] + self.obj["title"].split(" ") + self.obj["user"]["username"].split(" ")})
            if "/api/chan/thread/" in self.current_url:
                k = next(iter(self.obj), False)
                if k:
                    if "op" in self.obj[k]: self.current_catalog.append(self.obj[k]["op"])
                    if "posts" in self.obj[k]: self.current_catalog.extend(self.obj[k]["posts"].values())
            if "total" in self.obj and type(self.obj["total"]) == int:
                self.count = (100, self.obj["total"])
            if all(i in self.obj for i in ("media_id", "id", "tags", "pages", "title", "num_pages")):
                if self.current_query.endswith("/"):
                    self.current_catalog = [{"File URL": [f"https://i2.{self.current_url.strip('https://').split('api/v2')[0]}{i['path']}" for i in self.obj["pages"]]}]
                else:
                    self.current_catalog = [{"ID": self.current_url.split("://", 1)[-1].split("/", 1)[0] + "_" + str(self.obj["id"]), "Notes": "\n".join(tuple(i for i in self.obj["title"].values())).strip(), "File URL": f"https://t2.{self.current_url.strip('https://').split('api/v2')[0]}{self.obj['cover']['path']}", "Tags": [i["name"].replace(" ", "_") for i in self.obj["tags"]], "Source": self.current_query}]
            if any(i in self.obj for i in ("illust", "illusts")):
                il = []
                if "illust" in self.obj: il.append(self.obj["illust"])
                if "illusts" in self.obj: il.extend(self.obj["illusts"])
                if "next_url" in self.obj:
                    self.count = self.obj["next_url"]
                else:
                    self.count = "end"
                prefix = "" if getattr(Boards.list.default.get_model()[self.board], "engine", "") == "Pixiv" else "pixiv_"
                for p in il:
                    source = f"https://pixiv.net/artworks/{p['id']}"
                    notes = "\n".join([i for i in [p["title"], p["caption"]] if i])
                    tags = [i["translated_name"] or i["name"] for i in p["tags"]]
                    if p["illust_ai_type"] == 2: tags.append("ai_generated")
                    for i in [p["user"]["account"], p["user"]["name"], f"https://pixiv.net/users/{p['user']['id']}"]: tags.insert(0, i)
                    date = GLib.DateTime.new_from_iso8601(p["create_date"]).to_utc().to_unix()
                    if p["meta_single_page"]: self.current_catalog.append({"ID": prefix + str(p["id"]), "Tags": tags, "Created At": date, "Notes": notes.strip(), "Source": source, "File URL": p["meta_single_page"]["original_image_url"]})
                    else:
                        for n, i in enumerate(p["meta_pages"]): self.current_catalog.append({"ID": prefix + f"{p['id']}_{n}", "Tags": tags, "Created At": date, "Notes": notes.strip(), "Source": source, "File URL": i["image_urls"]["original"]})
            if "/api/v1/" in self.current_url:
                if "post" in self.obj:
                    self.obj = self.obj["post"]
                self.obj = [self.obj]
            if "post" in self.obj and type(self.obj["post"]) == list:
                if "@attributes" in self.obj:
                    self.count = (100, self.obj["@attributes"]["count"])
                self.current_catalog.extend(self.obj["post"])
                for i in self.current_catalog:
                    if "id" in i: i.setdefault("ID", i["id"])
                    if "change" in i: i.setdefault("Created At", i["change"])
                    if "source" in i: i.setdefault("Source", i["source"])
                    if type(i.get("tags", False)) == str:
                        i.setdefault("Tags", i["tags"].split(" "))
                        if i.get("has_children", False) == "true": i["Tags"].append(f"parent:{i['id']}")
                        p = i.get("parent_id", False)
                        if type(p) == int or (type(p) == str and p.isdigit()):
                            if int(p) > 0: i["Tags"].append(f"parent:{p}")
                    if "file_url" in i and "preview_url" in i: i.setdefault("File URL", i["preview_url"] if i["file_url"].endswith("zip") else i["file_url"])
            if "posts" in self.obj and type(self.obj["posts"]) == list: self.current_catalog.extend(self.obj["posts"])
            if "data" in self.obj and type(self.obj["data"]) == list:
                if "/manga/" in self.current_url:
                    if self.obj["total"] > (self.obj["offset"] + self.obj["limit"]):
                        self.count = self.current_url.split("offset=", 1)[0] + f"offset={self.obj['offset'] + self.obj['limit']}&" + self.current_url.split("offset=", 1)[-1].split("&", 1)[-1]
                    else:
                        self.count = ""
                    ll = []
                    for i in self.obj["data"]:
                        if i.get("attributes", {}).get("externalUrl", False):
                            url = i["attributes"]["externalUrl"]
                        elif i.get("attributes", {}).get("isUnavailable", False) or not i.get("id", False):
                            url = ""
                        elif i.get("id", False):
                            url = f"https://mangadex.org/chapter/{i['id']}"
                        chapter = {"URL": url, "Title": [], "Subtitle": []}
                        if "chapter" in i.get("attributes", {}):
                            chapter["Title"].append(f"<b>{i['attributes']['chapter']}</b>")
                        if "volume" in i.get("attributes", {}) and i["attributes"]["volume"]:
                            chapter["Title"].append(f"<b>({i['attributes']['volume']})</b>")
                        if "title" in i.get("attributes", {}):
                            chapter["Title"].append(GLib.markup_escape_text(i["attributes"]["title"] or ""))
                        if i.get("attributes", {}).get("externalUrl", False):
                            chapter["Title"].append("<span alpha='50%'>(external)</span>")
                        elif "pages" in i.get("attributes", {}):
                            chapter["Title"].append(f"<span alpha='50%'>({i['attributes']['pages']})</span>")
                        if "translatedLanguage" in i.get("attributes", {}) and i["attributes"]["translatedLanguage"]:
                            chapter["Title"].append(f"<span alpha='50%'>({i['attributes']['translatedLanguage'].upper()})</span>")
                        chapter["Title"] = " ".join([it.strip() for it in chapter["Title"] if it.strip()])
                        chapter["Subtitle"] = " ".join([it.strip() for it in chapter["Subtitle"] if it.strip()])
                        ll.append(chapter)
                    self.current_catalog = {"Chapters": ll}
                elif self.obj["data"]:
                    c = []
                    if len(self.obj["data"]) == 1:
                        covers = sorted(json(Online.Request(self.current_url.split("/manga", 1)[0] + "/cover?limit=100&manga[]=" + "&manga[]=".join([i["id"] for i in self.obj["data"]]), headers=self.current_headers))["data"], key=mangadex_volume_sort)
                        mangas = dict((i["id"], i) for i in self.obj["data"])
                        for i in covers:
                            id = next((it["id"] for it in i["relationships"] if it["type"] == "manga"), False)
                            if not id or not id in mangas: continue
                            it = mangas[id].copy()
                            it["File URL"] = f"https://mangadex.org/covers/{it['id']}/{i['attributes']['fileName']}"
                            c.append(it)
                        self.count = (len(c), len(c))
                    else: c.extend(self.obj["data"])
                    prefix = "" if getattr(Boards.list.default.get_model()[self.board], "engine", "") == "MangaDex" else "mangadex_"
                    for i in c:
                        tags = [it.lower().replace(" ", "_") for it in [next(iter(i["attributes"]["title"].values()), "")] + [next(iter(it.values()), "") for it in i["attributes"]["altTitles"]] + [next(iter(it["attributes"]["name"].values()), "") for it in i["attributes"]["tags"]] + [i["attributes"]["contentRating"]]]
                        self.current_catalog.append({"ID": prefix + i["id"], "Tags": tags, "File URL": i.get("File URL", f"https://mangadex.org/covers/{i['id']}/{next((it for it in i['relationships'] if it['type'] == 'cover_art'), {}).get('attributes', {}).get('fileName', "")}"), "Notes": next(iter(i["attributes"]["description"].values()), ""), "Source": f"https://mangadex.org/title/{i['id']}", "Created At": GLib.DateTime.new_from_iso8601(i["attributes"]["createdAt"]).to_utc().to_unix()})
            if "chapter" in self.obj and "baseUrl" in self.obj and "result" in self.obj and self.obj["result"] == "ok": self.current_catalog.append({"File URL": [f"{self.obj['baseUrl']}/data/{self.obj['chapter']['hash']}/{i}" for i in self.obj["chapter"]["data"]]})
            if "/api/chan/post/" in self.current_url and not self.current_catalog: self.current_catalog.append(self.obj)
        if type(self.obj) == list:
            if "/api/v1" in self.current_url:
                for post in self.obj:
                    if "error" in post: continue
                    created_at = GLib.DateTime.new_from_iso8601(post["published"], GLib.TimeZone.new_utc()).to_unix() if "published" in post else GLib.DateTime.new_now_utc().to_unix()
                    files = [post.get("file", {})] + post.get("previews", []) + post.get("attachments", [])
                    fs = []
                    for i in files:
                        if not "name" in i or not Gio.content_type_guess(i["name"])[0].startswith(("video", "image")): continue
                        if not any(it["path"] == i["path"] for it in fs): fs.append(i)
                    files = fs
                    base = "https://file." + self.current_url.split("://", 1)[-1].split("/api", 1)[0]
                    tags = post.get("tags", None)
                    if isinstance(tags, str):
                        tags = tags.lstrip("{").rstrip("}").split(",")
                    if not isinstance(tags, list):
                        tags = []
                    if "user" in post: tags.insert(0, str(post["user"]))
                    prefix = (post.get("service", "") + "-" + str(post.get("id", 0))).strip("-")
                    notes = ("\n".join([post.get("title", "\n"), post.get("content", "\n")])).strip("\n")
                    source = self.current_url.replace("/api/v1", "").rsplit("/post", 1)[0] + "/post/" + str(post.get("id", 0))
                    n = -1
                    for i in files:
                        n += 1
                        file_url = f'{i["server"] if "server" in i else base}/data{i["path"]}'
                        self.current_catalog.append({"ID": prefix + ("" if n == 0 else f"-{n + 1}"), "File URL": file_url if post.get("has_full", True) else (PostData.get_preview_url(file_url) or ""), "Tags": tags, "Notes": notes, "Source": source, "Created At": created_at})
                    if post.get("embed", False):
                        n += 1
                        self.current_catalog.append({"ID": prefix + ("" if n == 0 else f"-{n + 1}"), "File URL": post["embed"]["url"], "Tags": tags, "Notes": ("\n".join([post["embed"].get("subject", "\n"), post["embed"].get("description", "\n")])).strip(), "Source": source, "Created At": created_at})
                self.count = "end" if 50 > len(self.obj) else (self.current_url.split("?o=", 1)[0] + "?o=" + str(self.page * 50))
            if self.current_url.startswith("https://www.reddit.com/r/") and "/comments/" in self.current_url:
                _id = self.current_url.rsplit(".", 1)[0].rsplit("/", 1)[-1]
                if "media_metadata" in self.obj[0]["data"]["children"][0]["data"]:
                    for n, i in enumerate(self.obj[0]["data"]["children"][0]["data"]["media_metadata"].values()): self.current_catalog.append({"ID": "reddit_" + f"{_id}{('_' + str(n)) if n > 0 else ''}", "Notes": self.obj[0]["data"]["children"][0]["data"]["selftext"].strip(), "File URL": f"https://i.redd.it/{i['id']}.{i['m'].split('/')[-1]}", "Source": self.current_query})
                elif self.obj[0]["data"]["children"][0]["data"]["media"] and "reddit_video" in self.obj[0]["data"]["children"][0]["data"]["media"]: self.current_catalog.append({"ID": "reddit_" + _id, "Notes": "\n".join([self.obj[0]["data"]["children"][0]["data"]["title"], self.obj[0]["data"]["children"][0]["data"]["selftext"]]).strip(), "File URL": self.obj[0]["data"]["children"][0]["data"]["media"]["reddit_video"]["fallback_url"], "Source": self.current_query})
                else: self.current_catalog.append({"ID": "reddit_" + _id, "Notes": "\n".join([self.obj[0]["data"]["children"][0]["data"]["title"], self.obj[0]["data"]["children"][0]["data"]["selftext"]]).strip(), "File URL": self.obj[0]["data"]["children"][0]["data"]["url"], "Source": self.current_query})
            if all(type(i) == dict and "page" in i and "threads" in i for i in self.obj): self.current_catalog.extend([thread for i in self.obj for thread in i["threads"]])
            elif not ("/api/v1" in self.current_url or self.current_url.startswith("https://www.reddit.com/r/")): self.current_catalog.extend(self.obj)
            if "/posts.json?limit=100&page=" in self.current_url:
                for i in self.current_catalog:
                    if "id" in i: i.setdefault("ID", i["id"])
                    if "created_at" in i: i.setdefault("Created At", GLib.DateTime.new_from_iso8601(i["created_at"]).to_utc().to_unix())
                    if "source" in i: i.setdefault("Source", i["source"])
                    if "file_url" in i and "large_file_url" in i: i.setdefault("File URL", i["large_file_url"] if i["file_url"].endswith("zip") else i["file_url"])
                    i.setdefault("Tags", [])
                    i["Tags"].extend([tag for it in ("artist", "copyright", "character", "general", "meta") for tag in i.get(f"tag_string_{it}", "").split(" ") if tag])
                    if "rating" in i: i["Tags"].append(i["rating"])
                    if "id" in i and i.get("has_children", None): i["Tags"].append(f"parent:{i['id']}")
                    if i.get("parent_id", None): i["Tags"].append(f"parent:{i['parent_id']}")
                if not len(self.queries) > 1:
                    if self.next_page:
                        self.count = (100, self.tab.get_child().total)
                    elif self.page == 1 and 100 > len(self.current_catalog):
                        self.count = (100, len(self.current_catalog))
                    else:
                        try:
                            n = Online.Request(self.current_url.replace("/posts.json", "/counts/posts.json").replace("status:any", ""), headers=self.current_headers)
                            n = json(n.decode())
                            if "counts" in n and "posts" in n["counts"]:
                                self.count = (100, 0 if n["counts"]["posts"] == None else n["counts"]["posts"])
                        except: pass
        if "https://a.4cdn.org/" in self.current_url:
            board = self.current_url.split("https://a.4cdn.org/")[-1].split("/")[0]
            prefix = "" if getattr(Boards.list.default.get_model()[self.board], "engine", "") == "4chan" else f"4chan_{board}_"
            for i in self.current_catalog:
                i.setdefault("ID", prefix + str(i["no"]))
                i.setdefault("Created At", i["time"])
                if "filename" in i or "spoiler" in i:
                    i.setdefault("Tags", [])
                    i["Tags"].append(i["filename"] + i["ext"])
                    i["Tags"].append(str(i["tim"]) + i["ext"])
                    if i.get("spoiler", 0) == 1: i["Tags"].append("spoiler")
                if i.get("embed", ""): i.setdefault("File URL", i.get("embed", "").split('href="', 1)[-1].split('"', 1)[0])
                i.setdefault("File URL", f"https://i.4cdn.org/{board}/{i['tim']}{i['ext']}" if "tim" in i and "ext" in i else "")
                i.setdefault("Source", f"https://boards.4chan.org/{board}/thread/{i['no'] if i['resto'] == 0 else i['resto']}")
                i.setdefault("Notes", "\n".join((i.get("name", ""), i.get("sub", ""), i.get("com", ""))).strip("\n").strip())
        if "/_/api/chan/" in self.current_url:
            for i in self.current_catalog:
                if "num" in i: i.setdefault("ID", i["num"])
                if "timestamp" in i: i.setdefault("Created At", i["timestamp"])
                if i.get("embed", ""): i.setdefault("File URL", i.get("embed", "").split('href="', 1)[-1].split('"', 1)[0])
                i.setdefault("Tags", [])
                if i.get("media", False):
                    if i["media"].get("media_filename", ""): i["Tags"].append(i["media"]["media_filename"])
                    if i["media"].get("media_orig", ""): i["Tags"].append(i["media"]["media_orig"])
                    if i["media"].get("spoiler", 0) == 1: i["Tags"].append("spoiler")
                    if i["media"].get("remote_media_link", ""): i.setdefault("File URL", i["media"]["remote_media_link"])
                    if i["media"].get("media_link", ""): i.setdefault("File URL", i["media"]["media_link"])
                i.setdefault("Notes", "\n".join((i.get("name", "") or "", i.get("title_processed", "") or "", i.get("comment_sanitized", "") or "")).strip("\n").strip())
                if "thread_num" in i: i.setdefault("Source", f"{self.current_url.split('/_/', 1)[0]}/{self.current_url.split('board=', 1)[-1].split('&', 1)[0]}/thread/{i['thread_num']}")
        if "/catalog.json" in self.current_url or ("/res/" in self.current_url and self.current_url.endswith(".json")):
            base_url = self.current_url.split("/catalog.json")[0].split("/res/", 1)[0]
            for i in self.current_catalog:
                if "no" in i and "resto" in i:
                    i.setdefault("ID", str(i["no"]))
                    i.setdefault("Created At", i["time"])
                    if i.get("embed", ""): i.setdefault("File URL", i.get("embed", "").split('href="', 1)[-1].split('"', 1)[0])
                    if "filename" in i or "spoiler" in i:
                        i.setdefault("Tags", [])
                        i["Tags"].append(i["filename"] + i["ext"])
                        i["Tags"].append(str(i["tim"]) + i["ext"])
                        if i.get("spoiler", 0) == 1: i["Tags"].append("spoiler")
                    i.setdefault("Notes", "\n".join((i.get("name", ""), i.get("sub", ""), i.get("com", ""))).strip("\n").strip())
                    l = [i] + (i["extra_files"] if "extra_files" in i else [])
                    for it in l: it.setdefault("File URL", f"{base_url.strip('/').rsplit('/', 1)[0]}/static/deleted.svg" if "ext" in it and it["ext"] == "deleted" else ("https://" + EMBED_REGEX(it["embed"]).group(1).strip("https:").strip("//")) if "embed" in it and "src" in it["embed"] else f"{base_url}/src/{it['tim']}{it['ext']}" if "tim" in it and "ext" in it else "")
                    i.setdefault("Source", f"{base_url}/res/{i['no'] if i['resto'] == 0 else i['resto']}.html")

    def cardboard(self):
        q = getattr(Boards.list.default.get_model()[self.board], "url", "") + " " + " ".join(tuple(i for i in self.current_query.split(" ") if not i.lower().startswith("order:"))) + " " + getattr(Boards.list.default.get_model()[self.board], "append_to_search", "")
        q = q.strip()
        sort = tuple(i for i in self.current_query.split(" ") if i.lower().startswith("order:"))
        sort = sort[0].lower().split(":")[1] if sort else "Added"
        terms = tuple(i for i in q.split(" ") if i and not i.startswith(("-board:", "board:")))
        key_terms = tuple(i for i in terms if ":" in i and len(i.split(":")) == 2)
        terms = tuple(i.lower() for i in terms if not i in key_terms)
        try:
            key_terms = tuple([k.lstrip("-").replace("regex_", ""), Regex(v) if k.lstrip("-").startswith("regex_") else str(v), not k.startswith("-")] for k, v in tuple(i.split(":") for i in key_terms))
        except Exception as e:
            print(e)
            return
        for key in key_terms:
            if key[0] in PostData.default_names:
                key[0] = PostData.prop_get_title(key[0])
        term_boards = [i.replace("_", " ") for i in q.split(" ") if i.startswith(("-board:", "board:"))]
        if not tuple(i for i in term_boards if i.startswith("board:")):
            term_boards += [i.name for i in Boards if not tuple(it for it in term_boards if it.split(":")[-1] == i.name)]
        term_boards = tuple(i.split(":")[-1] for i in term_boards if not i.startswith("-") and i.split(":")[-1] in Boards.list.default.get_model())
        posts = App.default.data.read(table="Posts", conditions=" ".join("Board = ? OR" for _ in term_boards).strip(" OR"), conds=term_boards, return_dict=True, force_tuple=True)
        for p in posts:
            for k, v, i in key_terms:
                pv = str(p.get(k, ""))
                if hasattr(v, "search"):
                    _match = v.search(pv)
                    if _match:
                        _match = _match.group()
                else:
                    if k == "ID":
                        _match = pv == v
                    else:
                        _match = v in pv
                if (_match and not i) or (not _match and i): break
            else:
                tags = tuple(i.lower() for i in json(p.get("Tags", "[]")))
                for term in terms:
                    if term.startswith("-") and term.lstrip("-") in tags or not term.startswith("-") and not term in tags: break
                else: self.current_catalog.append(p)
        if "random" in sort:
            k = return_random_500
        else:
            def k(p):
                r = p.get(PostData.prop_get_title(sort.split("_asc")[0]), None)
                return alphabetical_sort(r if r != None else p.get("Added", 0))
        self.current_catalog.sort(key=k, reverse=not "_asc" in sort)
        self.current_catalog = self.current_catalog[(self.page - 1) * 25:]
        self.count = "end"

    def url_from_url(self, force_engine=False):
        if self.engine == "vichan":
            if "/res/" in self.current_url:
                self.current_url = self.current_url.rsplit(".", 1)[0] + ".json"
            elif not "/src/" in self.current_url:
                self.current_url = self.current_url.strip("/") + "/catalog.json"
            return
        if self.engine == "FoolFuuka":
            if "/_/api/chan" in self.current_url: return
            elif "/thread/" in self.current_url:
                board = self.current_url.split("/thread/", 1)[0].rsplit("/", 1)[-1]
                base = self.current_url.split(f"/{board}/", 1)[0].strip("/")
                if "#" in self.current_url and self.current_url.rsplit("#", 1)[-1].strip("p").isdigit():
                    self.current_url = f"{base}/_/api/chan/post/?board={board}&num={self.current_url.rsplit('#', 1)[-1].strip('p')}"
                else:
                    self.current_url = f"{base}/_/api/chan/thread/?board={board}&num={self.current_url.split('/thread/', 1)[-1].split('/', 1)[0]}"
            elif force_engine: self.url_from_query("", self.current_url.split("/thread", 1)[0].strip("/"))
        if self.engine == "Danbooru" and ("/post/show/" in self.current_url or "/posts/" in self.current_url): self.url_from_query("id:" + self.current_url.replace("/post/show/", "/posts/").split("?")[0].split("/posts/")[-1], "https://" + self.current_url.split("https://", 1)[-1].split("/",1)[0])
        if self.engine == "Gelbooru" and "id=" in self.current_url: self.url_from_query("id:" + self.current_url.split("id=")[-1].split("&")[0], "https://" + self.current_url.split("https://", 1)[-1].split("/",1)[0])
        if self.engine == "Moebooru" and "/post/show/" in self.current_url: self.url_from_query("id:" + self.current_url.split("?")[0].split("/post/show/")[-1].split("/")[0], "https://" + self.current_url.split("https://", 1)[-1].split("/",1)[0])
        if self.engine in ("Danbooru", "Gelbooru", "Moebooru") and (force_engine or "?" in self.current_url and "tags=" in self.current_url): self.url_from_query(GLib.Uri.parse_params(self.current_url.split("?")[-1], -1, "&", GLib.UriParamsFlags.NONE)["tags"].replace(" + ", " ") if "?" in self.current_url and "tags=" in self.current_url else "", "https://" + self.current_url.split("https://", 1)[-1].split("/",1)[0])

    def url_from_query(self, query, url):
        if is_online(query):
            self.current_url = query
        else:
            query = GLib.Uri.escape_string(query)
        if self.engine == "Danbooru":
            self.current_url = f"{url}/posts.json?limit=100&page={self.page}&tags={query}"
        if self.engine == "Gelbooru":
            self.current_url = f"{url}/index.php?limit=100&pid={self.page - 1}&page=dapi&s=post&q=index&json=1&tags={query}"
        if self.engine == "Moebooru":
            self.current_url = f"{url}/post.xml?limit=100&page={self.page}&tags={query}"
        if self.engine == "FoolFuuka":
            self.current_url = f"{url.rsplit('/', 1)[0]}/_/api/chan/post/?board={url.rsplit('/', 1)[1]}&num={query.split('id:')[-1]}" if query.startswith("id:") else f"{url.rsplit('/', 1)[0]}/_/api/chan/gallery/?board={url.rsplit('/', 1)[1]}&page={self.page}{query.strip('$') if query.startswith('$') else ''}"
        if self.engine == "vichan":
            self.current_url = f"{url}/catalog.json"

    def query_to_url(self):
        bd = Boards.list.default.get_model()[self.board]
        if self.current_query.startswith(("archive://", "file://")):
            self.engine = bd.engine if bd else "Cardboard"
            return
        original_query = self.current_query
        self.current_query = self.current_query.strip("\n").strip()
        if is_online(self.current_query):
            for i in Boards:
                if i.engine == "FoolFuuka" and "4chan.org/" in self.current_query and i.url.endswith("/" + self.current_query.split("org/", 1)[-1].split("/", 1)[0]):
                    self.board = i.name
                    self.current_query = i.url + "/" + self.current_query.split("org/", 1)[-1].split("/", 1)[-1]
                if (i.url and self.current_query.startswith(i.url)) or any(i.engine == a and b in self.current_query for a, b in (("4chan", f"4chan.org/{i.url}/thread"), ("MangaDex", "mangadex.org/"), ("Pinterest", "pinterest.com/"))):
                    self.board = i.name
        bd = Boards.list.default.get_model()[self.board] or Boards.list.default.get_model()[0]
        self.engine, url, self.current_url = bd.engine, bd.url, self.current_query
        if self.current_url.startswith("https://weebcentral.com/"):
            if "/chapters/" in self.current_url:
                self.current_url = self.current_url.rstrip("/") + "/images"
            if "/series/" in self.current_url and not len(self.current_url.split("/series/", 1)[-1].split("/", -1)) == 2:
                self.current_url = self.current_url.split("/series/", 1)[0].rstrip("/") + "/series/" + self.current_url.rsplit("/series/", 1)[-1].split("/", 1)[0].strip("/") + "/full-chapter-list"
        if self.current_query.startswith(("https://x.com/", "https://xcancel.com", "https://nitter.net/")) or self.engine == "Nitter" and not is_online(self.current_query):
            self.engine = "Nitter"
            global NITTER_INSTANCE
            if bd.engine == "Nitter" and bd.url and bd.url.rstrip("/"):
                NITTER_INSTANCE = bd.url.rstrip("/")
            else:
                try:
                    NITTER_INSTANCE = NITTER_INSTANCE or False
                except Exception as ex:
                    NITTER_INSTANCE = (GLib.getenv("NITTER_INSTANCE") or "").rstrip("/")
                if not NITTER_INSTANCE:
                    instances = [i.split("\"", 1)[0].rstrip("/") for i in Online.Request("https://xxcancel.com/").decode().rsplit("instance-list\">", 1)[-1].split("<p>", 1)[0].split("href=\"")[1:-1]]
                    for i in instances:
                        if i in NITTER_SKIP: continue
                        r = repr(Online.Request(i + "/X/search", headers=NITTER_HEADERS).decode().strip().replace("\n", "").replace(";", "").replace("\\", ""))
                        if "This website is running Anubis" in r or "challenge-error-text" in r or "Enter search..." in r:
                            NITTER_INSTANCE = i
                            break
                        else: NITTER_SKIP.append(i)
            if NITTER_INSTANCE:
                start = self.current_query.split("://", 1)[-1].split("/", 1)[-1]
                user = start.split("/", 1)[0] if not start.startswith("search") else ""
                if "id:" in self.current_query or "/status/" in self.current_query:
                    self.current_url = f"{NITTER_INSTANCE}/i/status/{self.current_query.split('/status/')[-1].split('#')[0].split('id:')[-1].split(' ')[0]}?prefs=hideTweetStats=on,hideBanner=on,hidePins=on,hideReplies=on,hideCommunityNotes=on,proxyVideos=,replaceTwitter=,replaceYouTube=,replaceReddit="
                elif user:
                    self.current_url = f"{NITTER_INSTANCE}/{user}/search?f-media=on&prefs=hideTweetStats=on,hideBanner=on,hidePins=on,hideReplies=on,hideCommunityNotes=on,proxyVideos=,replaceTwitter=,replaceYouTube=,replaceReddit=&q={self.current_query.split('q=')[-1] if 'q=' in self.current_query else '' if self.current_query.startswith(('https://', 'http://')) else self.current_query}"
                else:
                    self.current_url = f"{NITTER_INSTANCE}/search?f=tweets&f-media=on&prefs=hideTweetStats=on,hideBanner=on,hidePins=on,hideReplies=on,hideCommunityNotes=on,proxyVideos=,replaceTwitter=,replaceYouTube=,replaceReddit=&q={self.current_query.split('q=')[-1] if 'q=' in self.current_query else '' if self.current_query.startswith(('https://', 'http://')) else self.current_query}"
            else: Task.invoke(Toast, "No Nitter instance available")
        if self.current_query.startswith("https://") and "pinterest.com/" in self.current_query or self.engine == "Pinterest" and not is_online(self.current_query):
            self.engine = "Pinterest"
            self.page = 1
            if "/pin/" in self.current_query and self.current_query.endswith("/"):
                self.current_url = f"https://www.pinterest.com/resource/RelatedPinFeedResource/get/?data={json_string({'options': {'pin': self.current_query.split('/pin/', 1)[-1].strip('/'), 'add_vase': True, 'pins_only': True, 'bookmarks': None}})}&source_url="
            elif "/pin/" in self.current_query or "id:" in self.current_query:
                self.current_url = f"https://www.pinterest.com/resource/PinResource/get/?data={json_string({'options': {'id': self.current_query.split('/pin/', 1)[-1].split('id:', 1)[-1], 'field_set_key': 'detailed'}})}&source_url="
            elif self.current_query.startswith("https://") and not "?q=" in self.current_query:
                user = self.current_query.strip("/").split(".com/", 1)[-1].rsplit("/", 1)[0].split(" ")[0]
                q = self.current_query.strip("/").rsplit("/", 1)[-1].replace("  ", " ").strip().replace(" ", "-")
                b = json(Online.Request(f"https://www.pinterest.com/resource/BoardResource/get/?data={json_string({'options': {'slug': q, 'username': user, 'field_set_key': 'detailed'}})}&source_url=", headers=PINTEREST_HEADERS))
                self.current_url = f"https://www.pinterest.com/resource/BoardFeedResource/get/?data={json_string({'options': {'board_id': b['resource_response']['data']['id'], 'field_set_key': 'react_grid_pin', 'prepend': False, 'bookmarks': None}})}&source_url="
            else:
                i = (bd.url if bd.engine == self.engine else "").split("://", 1)[-1].rsplit("/", 1)[-1]
                self.current_url = f"https://www.pinterest.com/resource/BaseSearchResource/get/?data={json_string({'options': {'query': self.current_query.split('?q=', 1)[-1].split('&')[0] + i, 'scope': 'pins', 'rs': 'typed', 'bookmarks': None}})}&source_url="
        if self.current_query.startswith("https://boards.4chan.org/") or self.engine == "4chan" and not is_online(self.current_query):
            self.engine, url = "4chan", self.current_query.split(".org/")[-1].split("/")[0] if is_online(self.current_query) else url
            if "/thread/" in self.current_query:
                self.current_url = self.current_query.replace("boards.", "").replace("4chan.", "a.4cdn.").rstrip(".json").rstrip("/")
                if not self.current_url.rsplit("/", 1)[-1].isdigit():
                    self.current_url = self.current_url.rsplit("/", 1)[0]
                self.current_url += ".json"
            else:
                self.current_url = f"https://a.4cdn.org/{url.split('://', 1)[-1].split('/', 1)[-1].split('/', 1)[0]}/catalog.json"
        if self.current_query.replace("www.", "").startswith("https://pixiv.net") or self.engine == "Pixiv" and not is_online(self.current_query):
            self.engine = "Pixiv"
            if "p=" in self.current_query and self.current_query.split("p=", 1)[-1].split("&")[0].isdigit():
                self.page = int(self.current_query.split("p=", 1)[-1].split("&")[0])
            if "/users/" in self.current_query:
                self.current_url = f"https://app-api.pixiv.net/v1/user/illusts?user_id={self.current_query.split('/users/')[-1]}"
            elif "/artworks/" in self.current_query:
                self.current_url = f"https://app-api.pixiv.net/v1/illust/detail?illust_id={self.current_query.split('/artworks/', 1)[-1]}"
            else:
                self.current_url = f'https://app-api.pixiv.net/v1/search/illust?word={self.current_query.split("/search?q=")[-1].split("/tags/")[-1].split("&")[0].split("/")[0]}' + (bd.url if bd.engine == self.engine else "").split("://", 1)[-1].rsplit("/", 1)[-1]
            if self.page > 1:
                self.current_url += f"&offset={30 * (self.page - 1)}"
            if self.engine == bd.engine:
                self.current_url += bd.append_to_search
        if self.current_query.replace("www.", "").replace("api.", "").startswith("https://mangadex.org") or self.engine == "MangaDex" and not is_online(self.current_query):
            self.engine = "MangaDex"
            if "/title/" in self.current_query:
                original_query = self.current_query = self.current_query.split("title/", 1)[0] + "title/" + self.current_query.split("title/", 1)[-1].split("/", 1)[0] + ("/" if "/" in self.current_query.split("title/", 1)[-1] else "")
            if "api.mangadex.org" in self.current_query:
                self.current_url = self.current_query
            if "/chapter/" in self.current_query:
                self.current_url = f"https://api.mangadex.org/at-home/server/{self.current_query.strip('/').split('/chapter/')[-1].rsplit('/', 1)[-1]}?forcePort443=false"
            elif "/title/" in self.current_query and self.current_query.endswith("/"):
                self.current_url = f"https://api.mangadex.org/manga/{self.current_query.split('/title/')[-1].strip('/').rsplit('/', 1)[-1]}/feed?limit=500&order[volume]=desc&order[chapter]=desc&offset=0"
            else:
                q = self.current_query
                if "id:" in q or "/title/" in q and not q.endswith("/"):
                    q = "$&ids[]=" + q.split(":")[-1].split("/title/", 1)[-1]
                q += (bd.url if bd.engine == self.engine else "").split("://", 1)[-1].rsplit("/", 1)[-1]
                self.current_url = "https://api.mangadex.org/manga?includes[]=cover_art&limit=100&offset=" + str((self.page - 1) * 100 if self.page > 1 else 0) + ((q.strip('$') if q.startswith('$') else '&title=\'' + q + '\'') if q else '')
            if self.engine == bd.engine:
                self.current_url += bd.append_to_search
            else:
                try:
                    global MANGADEX_RATINGS
                    MANGADEX_RATINGS = MANGADEX_RATINGS or False
                except Exception as ex:
                    MANGADEX_RATINGS = False
                if not MANGADEX_RATINGS:
                    r = Online.Request(self.current_url + "&contentRating[]=", headers={"User-Agent": "Cardboard"}).decode()
                    j = json(r)
                    if "errors" in j:
                        MANGADEX_RATINGS = j["errors"][0]["detail"].rsplit("[", 1)[-1].split("]", 1)[0].replace("\"", "").split(",")
                    else:
                        self.text, self.obj = r, j
                if MANGADEX_RATINGS:
                    for i in MANGADEX_RATINGS:
                        self.current_url += f"&contentRating[]={i}"
        if is_online(self.current_query):
            if "/g/" in self.current_query and self.current_query.strip("/").split("/g/", 1)[-1].split("/")[0].isdigit():
                self.current_url = self.current_query.split("/g/", 1)[0] + "/api/v2/galleries/" + self.current_query.strip("/").split("/g/", 1)[-1].split("/")[0]
            if "youtu.be/" in self.current_query or "youtube.com" in self.current_query:
                self.current_url = self.current_query.replace("youtu.be/", "youtube.com/watch?v=").replace("/shorts/", "/watch?v=")
            if self.current_query.startswith("https://www.reddit.com/r/") and "/comments/" in self.current_query:
                self.current_url, _id = self.current_query.split("/comments/", 1)
                self.current_url += "/comments/" + (_id.split("/")[0] if "/" in _id else _id) + ".json"
            if "artstation.com/artwork/" in self.current_query:
                self.current_url = f"{self.current_query.replace('artwork', 'projects')}.json"
            if self.current_query.startswith("https://www.zerochan.net/") and self.current_query.split("/")[-1].isdigit():
                self.current_url = self.current_query + "?&json"
            if "pbs.twimg.com/media/" in self.current_query:
                if "." in self.current_query.split("/media/")[-1]:
                    self.current_url = self.current_query.split("?", 1)[0] + "?name=orig"
            if "catbox.moe" in self.current_url:
                self.engine = "Cardboard"
            self.url_from_url()
        else:
            if self.engine in ("Danbooru", "Gelbooru", "Moebooru", "FoolFuuka", "vichan"): self.url_from_query(self.current_query, url)
            if self.engine == bd.engine:
                self.current_url += bd.append_to_search
            self.current_url = self.current_url.replace("= ", "=")
        self.current_query = self.current_query if self.engine == bd.engine else original_query
        self.board = self.board if Boards.list.default.get_model()[self.board] else Boards.list.default.get_model()[0].name

def is_chapter(u): return "mangadex.org/" in u and "/chapter/" in u or "/g/" in u and u.split("/g/", 1)[-1].split("/")[0].isdigit()

def is_chapters(u):
    v = "mangadex.org/" in u and "/title/" in u and u.endswith("/")
    v = v or ("weebcentral.com" in u and "/series/" in u and not len(u.split("/series/", 1)[-1].split("/", -1)) == 2)
    return v

def is_thread(u, engine): return "boards.4chan.org/" in u and "/thread/" in u or "/res/" in u and engine == "vichan" or engine == "FoolFuuka" and "/thread/" in u

def get_attribute(s, n, default=""):
    v = f"{n}="
    if not v in s: return str(default)
    r = s.split(v, 1)[-1]
    r = r.split(r[:1] + ">", 1)[0].split(r[:1] + " ", 1)[0]
    return r.strip("\n\"'>")

def get_paintables(widgets=False):
    paintables = {} if widgets else []
    for i in Tab.get_all():
        c = i.get_child()
        if hasattr(c, "get_posts"):
            if widgets:
                for it in c.get_posts():
                    paintables.setdefault(it.get_paintable(), [])
                    paintables[it.get_paintable()].append(it)
            else: paintables.extend([i.get_paintable() for i in c.get_posts()])
        if hasattr(c, "get_paintable"):
            if widgets:
                paintables.setdefault(c.get_paintable(), [])
                paintables[c.get_paintable()].append(c)
            else:
                paintables.append(c.get_paintable())
    if widgets: return paintables
    else: return [i for i in paintables if hasattr(i, "uri")]

def open_files(files):
    if not Window.current:
        d = App.default.data.read(table="Windows", column="ID", force_tuple=True)
        if not d:
            App.default.data.set_default(table="Windows", conditions="ID = '1'", values=(1,), names=("ID",))
            d = [1]
        for i in d: Window(i)
    t = None
    for i in files: Tab.create(query=(("file://" if not i.startswith(("archive://", "file://", "https://", "http://")) else "") + i) if isinstance(i, str) else i.get_uri(), page=1, board=False)
    return App.default.get_active_window().present()

def activate(a): return App.default.get_active_window().present() if App.default.get_active_window() else open_files(ARGS[1:])
def file_open(a, files, *_): open_files(files)
def do_open_uri(p, r):
    if r != "confirm": return
    uris = str_to_list(p.get_extra_child().get_row(0).get_text())
    if uris: open_files(uris)
def open_uris(*_):
    group = Adw.PreferencesGroup()
    group.add(URIRow())
    Prompt(callback=do_open_uri, confirm_callback=False, heading="Open URIs", extra_child=group).present(Window.current)

def download(*_):
    selected_child = App.default.get_active_window().stack.get_visible_child().get_selected_page().get_child().get_child()
    if isinstance(selected_child, Post): selected_child.download()

def overview(*_):
    visible_child = App.default.get_active_window().stack.get_visible_child()
    visible_child.overview.set_open(not visible_child.overview.get_open())

def reopen_tab(*_):
    if Tab.closed:
        q = Tab.closed.pop(-1)
        while q in Tab.closed: Tab.closed.remove(q)
        Tab.create(query=q[0], page=q[1], board=q[2])
        App.default.lookup_action("reopen-tab").set_enabled(bool(Tab.closed))

def mangadex_volume_sort(i): return alphabetical_sort(i.get("attributes", {}).get("volume", 0))

def id_sort(i): return int(i.get("ID", "0") or 0)

ITEM_REGEX = Regex(r"<item>\s*<title>(?P<Title>.*?)</title>\s*<link>(?P<URL>.*?)</link>", DOTALL)
POST_REGEX = Regex(r'<post\b([^>]*)>(?:.*?</post>)?')
ATTR_REGEX = Regex(r'(\w[\w:-]*)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'/>]+)))?')
EMBED_REGEX = Regex(r'src="(.*?)"').search

NITTER_SKIP = []
NITTER_HEADERS = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Sec-Fetch-Dest": "document"}

PINTEREST_HEADERS = {"Accept": "application/json, text/javascript, */*, q=0.01", "X-Requested-With": "XMLHttpRequest",
"X-APP-VERSION": "a89153f", "X-Pinterest-AppState": "active", "X-Pinterest-Source-Url": "", "X-Pinterest-PWS-Handler": "www/[username].js",
"Alt-Used": "www.pinterest.com", "Connection": "keep-alive", "Cookie": "", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin"}
INFO = {
    "ID": "io.github.kirukomaru11.Cardboard",
    "Developer": "きるこ丸11号",
    "Comment": "Browse imageboards",
    "Issue URL": "https://github.com/kirukomaru11/Cardboard/issues",
    "Website": "https://github.com/kirukomaru11/Cardboard",
    "Keywords": ["Booru", "Imageboard", "Browser", "Gallery", "Catalog"],
    "Categories": ["Network", "AudioVideo", "Graphics"],
    "Branding": ["#d5b8a0", "#b5835a"],
    "MimeTypes": [i for i in Gio.content_types_get_registered() if i.startswith(("audio/", "video/", "image/"))],
}

APP_CSS = r"""
chapters listview { font-size: 24px; }
chapters listview row { margin-bottom: 20px; }
tabbar:not(.visible) separator { opacity: 0; }
tabbar:not(.visible) tab:selected:not(:hover) { background: none; }
tabbar:not(.visible) tab:selected:not(:hover) button,
tabbar:not(.visible) tab:selected:not(:hover) button image { -gtk-icon-source: none; -gtk-icon-size: 1px; opacity: 0; padding: 0px; margin: 0px; min-height: 0px; min-width: 0px; }

label.quote, label.greentext { color: var(--green-3); }
label.rquote { color: var(--red-2); font-style: italic; }
label .link { text-decoration-style: unset; text-decoration-color: transparent; text-decoration: none; color: var(--blue-4); }
label.spoiler { padding: 0px 4px; margin: 0px 2px; background: var(--dark-5); color: var(--dark-5); transition: color 0.3s; border-radius: 4px; }
label.spoiler:hover { color: var(--light-1); }
label.spoiler .link { color: var(--dark-5); transition: color 0.3s; }
label.spoiler:hover .link { color: var(--light-1); }
label.bold { font-weight: bold; }
label.italic { font-style: italic; }
label.code { font-family: monospace; }

thread viewport > box { border-spacing: 10px; font-size: 20px; margin-bottom: 10px; }
reply { transition: background-color 0.3s; margin: 0px 10px; border-radius: 10px; padding: 10px; background: var(--shade-color); }
reply header { border-spacing: 8px; }
reply.op { background: none; margin: 0px; padding: 0px 10px; }
reply media { margin: 4px 0px; min-width: 120px; min-height: 50px; }
thread reply.highlight { background: color-mix(in srgb, var(--shade-color) 90%, var(--window-fg-color)); }

.bottom-bar search { margin: 4px 6px 2px 6px; }
search {
 min-height: 34px;
 border-spacing: 8px;
 border-radius: 10px;
 background: color-mix(in srgb, currentColor 8%, transparent);
 outline: 0 solid transparent;
 outline-offset: 4px;
 transition: outline-color 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94), outline-width 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94), outline-offset 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
 padding: 0px 15px;
}
search placeholder { opacity: var(--dim-opacity); }
search:focus-within { outline-color: color-mix(in srgb, var(--accent-color) 50%, transparent); outline-width: 2px; outline-offset: -2px; }
search button { outline: none; font-weight: normal; }

@keyframes loading-pulse {
  0%, 100% { outline-color: var(--accent-color); }
  50%      { outline-color: var(--accent-fg-color); }
}

.searching {
   outline: 2px solid transparent;
   outline-offset: -2px;
   animation-name: loading-pulse;
   animation-duration: 2s;
   animation-timing-function: ease-in-out;
   animation-iteration-count: infinite;
}

.boards listview { margin: 0px; padding: 0px; }
.boards listview row { margin: 0px; padding: 0px; }
.boards listview row label { padding: 0px 8px; border-radius: 9px; }
.boards > contents > box { border-spacing: 10px; }
.boards scrolledwindow scrollbar range trough slider { min-height: 18px; }

:drop(active) label.highlight { box-shadow: 0 0 0 1px var(--accent-bg-color) inset; }

before { transition: box-shadow 0.4s, background-size 0.4s, background-image 0.4s; border-radius: 13px; background-repeat: no-repeat; background-position: center; background-size: 20%; color: white; box-shadow: 0 0 0 4px transparent inset; filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.3)); }
tab > post before { background-size: 8%; }
post { border-radius: 13px; }
post.not-media { font-weight: bold; min-height: 200px; font-size: 20px; background: black; color: white; }
tab > post { border-radius: 0px; }
post:hover > replies { opacity: 1; backdrop-filter: blur(20px) brightness(0.6); }
post > replies { color: white; opacity: 0; transition: opacity 0.3s; font-size: 22px; font-weight: bold; border-radius: 0px 0px 10px 0px; padding: 6px 6px 6px 6px; }
post > box > media,
post > box > media picture { border-radius: 0px; }
post intro { background: var(--shade-color); padding: 2px; font-size: 20px; }
.small :not(tab) > post:not(.playing):not(.adding):not(.removing).preview.animated before,
:not(tab) > post:not(.playing):not(.adding):not(.removing).preview.animated:hover before {
background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' height='300px' viewBox='0 0 16 16' width='300px'%3E%3Cpath d='m 2 13.492188 v -11 c 0 -1.5 1.265625 -1.492188 1.265625 -1.492188 h 0.132813 c 0.242187 0 0.484374 0.054688 0.699218 0.175781 l 9.796875 5.597657 c 0.433594 0.238281 0.65625 0.730468 0.65625 1.222656 c 0 0.492187 -0.222656 0.984375 -0.65625 1.226562 l -9.796875 5.597656 c -0.214844 0.121094 -0.457031 0.175782 -0.699218 0.171876 h -0.132813 s -1.265625 0 -1.265625 -1.5 z m 0 0' fill='#FFFFFF'/%3E%3C/svg%3E%0A")
no-repeat center / 16%;
}
.small :not(tab) > post:not(.playing):not(.adding):not(.removing).preview.animated before,
.small before { background-size: 30% ; }
.small .preview.has-notes before,
:not(tab) > .preview.has-notes:hover before { box-shadow: 0 0 0 4px var(--green-5) inset; }
.small :not(tab):not(reply) > :not(.has-intro).preview.parent before,
:not(tab):not(reply) > :not(.has-intro).preview.parent:hover before { box-shadow: 0 0 0 4px var(--green-2) inset; }
.small :not(tab) > .preview.chapters before,
:not(tab) > .preview.chapters:hover before { box-shadow: 0 0 0 4px var(--blue-4) inset; }
.small :not(tab):not(reply) > .preview.child before,
:not(tab):not(reply) > .preview.child:hover before { box-shadow: 0 0 0 4px var(--orange-2) inset; }
.small :not(tab) > .preview.chapter before,
:not(tab) > .preview.chapter:hover before { box-shadow: 0 0 0 4px var(--purple-1) inset; }
.small :not(tab) > .preview.parent.child before,
:not(tab) > .preview.parent.child:hover before { box-shadow: 0 0 0 4px var(--red-1) inset; }
window.small:not(.Cardboard) :not(tab) > post.preview.starred before,
window:not(.Cardboard) :not(tab) > post.preview.starred:hover before { box-shadow: 0 0 0 4px var(--yellow-3) inset; }
window.small :not(tab) > post.preview.local-preview.local before,
window :not(tab) > post.preview.local-preview.local:hover before { box-shadow: 0 0 0 4px var(--dark-1) inset; }
window manga picture.selected { outline: 4px var(--blue-2) solid; }
window post.selected before { box-shadow: 0 0 0 4px var(--blue-2) inset; }
post.removing before {
background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" height="300px" viewBox="0 0 16 16" width="300px"><path d="m 8 0 c -0.429688 0 -0.8125 0.273438 -0.949219 0.683594 l -1.449219 4.339844 l -4.589843 -0.015626 c -0.4375 0 -0.828125 0.28125 -0.9609378 0.695313 c -0.1328124 0.417969 0.0195313 0.871094 0.3789068 1.125 l 3.625 2.554687 l -1.5 4.285157 c -0.140626 0.40625 -0.011719 0.855469 0.328124 1.121093 c 0.335938 0.261719 0.804688 0.285157 1.164063 0.050782 l 4.003906 -2.59375 l 3.898438 2.589844 c 0.355469 0.234374 0.824219 0.21875 1.164062 -0.046876 c 0.339844 -0.261718 0.472657 -0.714843 0.332031 -1.117187 l -1.503906 -4.289063 l 3.644532 -2.578124 c 0.351562 -0.25 0.503906 -0.703126 0.371093 -1.113282 c -0.128906 -0.414062 -0.511719 -0.695312 -0.945312 -0.699218 l -4.660157 -0.015626 l -1.402343 -4.285156 c -0.132813 -0.410156 -0.515625 -0.68749975 -0.949219 -0.691406 z m -0.007812 4.1875 l 0.683593 2.097656 c 0.136719 0.410156 0.515625 0.6875 0.945313 0.6875 l 2.253906 0.007813 l -1.703125 1.203125 c -0.363281 0.257812 -0.511719 0.726562 -0.363281 1.148437 l 0.765625 2.191407 l -1.964844 -1.304688 c -0.332031 -0.21875 -0.761719 -0.222656 -1.097656 -0.007812 l -2.101563 1.363281 l 0.785156 -2.242188 c 0.148438 -0.421875 -0.003906 -0.890625 -0.367187 -1.148437 l -1.652344 -1.164063 l 2.144531 0.007813 c 0.429688 0 0.816407 -0.277344 0.949219 -0.683594 z m 0 0" fill="#FFFFFF60"/></svg>')
no-repeat center / 40%;
}
post.adding before {
background: url("data:image/svg+xml,%3Csvg height='300px' viewBox='0 0 16 16' width='300px' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='m 8 0 c -0.429688 0 -0.8125 0.273438 -0.949219 0.683594 l -1.449219 4.339844 l -4.589843 -0.015626 c -0.980469 -0.003906 -1.382813 1.257813 -0.582031 1.820313 l 3.625 2.554687 l -1.5 4.285157 c -0.316407 0.902343 0.6875 1.691406 1.492187 1.171875 l 4.003906 -2.59375 l 3.894531 2.585937 c 0.800782 0.53125 1.816407 -0.257812 1.5 -1.160156 l -1.503906 -4.289063 l 3.644532 -2.578124 c 0.789062 -0.5625 0.394531 -1.808594 -0.574219 -1.8125 l -4.660157 -0.015626 l -1.402343 -4.285156 c -0.132813 -0.410156 -0.515625 -0.68749975 -0.949219 -0.691406 z m 0 0' fill='#FFFFFF'/%3E%3C/svg%3E%0A")
no-repeat center / 40%;
}
tab > post.removing before,
tab > post.adding before { background-size: 12%; }
.small .adding before,
.small .removing before { background-size: 40%; }

sheet,
window,
controls.toolbar.card,
toolbarview.overview { transition: background 0.4s ease; }
.colored {
  --scrollbar-outline-color: rgb(0 0 0 / 25%);
  --accent-color: var(--color-1);
  --accent-bg-color: var(--color-1);
  --popover-bg-color: color-mix(in srgb, var(--color-2), var(--window-bg-color) 60%);
  --card-bg-color: rgb(255 255 255 / 4%);
}
.colored,
.colored sheet {
  background: linear-gradient(to bottom right, color-mix(in srgb, var(--color-1) 45%, transparent), transparent),
    linear-gradient(to bottom left, color-mix(in srgb, var(--color-2) 45%, transparent), transparent),
    linear-gradient(to top, color-mix(in srgb, var(--color-3) 45%, transparent), transparent),
    var(--window-bg-color);
}
.colored controls.toolbar.card { background: color-mix(in srgb, var(--color-3), transparent 60%); }
.colored toolbarview.overview { background: none; }"""

DATA_INIT = """
CREATE TABLE IF NOT EXISTS Boards (ID INTEGER, Name TEXT NOT NULL UNIQUE, Engine TEXT NOT NULL DEFAULT 'Cardboard', URL TEXT DEFAULT '', 'Append to Search' TEXT DEFAULT '', 'Search Autocomplete' INTEGER NOT NULL DEFAULT 1, 'Launch Sources' INTEGER NOT NULL DEFAULT 0, 'Download Favorites' INTEGER NOT NULL DEFAULT 0, 'Download Thumbnails' INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS Posts (Board TEXT NOT NULL DEFAULT 'Favorites', ID TEXT NOT NULL, Added INTEGER NOT NULL DEFAULT (unixepoch()), 'Created At' INTEGER NOT NULL DEFAULT (unixepoch()), 'File URL' TEXT DEFAULT '', Source TEXT DEFAULT '', Notes TEXT DEFAULT '', Tags TEXT NOT NULL DEFAULT '[]', UNIQUE ('Board', 'ID'), FOREIGN KEY (Board) REFERENCES Boards(Name) ON DELETE CASCADE ON UPDATE CASCADE);
CREATE TABLE IF NOT EXISTS Tabs (Window INTEGER NOT NULL DEFAULT 1, TabView INTEGER NOT NULL DEFAULT 1, ID INTEGER, Query TEXT DEFAULT '', Page INTEGER NOT NULL DEFAULT 1, Board TEXT NOT NULL DEFAULT 'Favorites', UNIQUE ('Window', 'TabView', 'ID'), FOREIGN KEY (Board) REFERENCES Boards(Name) ON DELETE CASCADE ON UPDATE CASCADE, FOREIGN KEY (Window) REFERENCES Windows(ID) ON DELETE CASCADE ON UPDATE CASCADE);
CREATE TABLE IF NOT EXISTS Windows (ID INTEGER PRIMARY KEY AUTOINCREMENT, 'Manga Width' INTEGER NOT NULL DEFAULT 500, 'Default Width' INTEGER NOT NULL DEFAULT 360, 'Default Height' INTEGER NOT NULL DEFAULT 760, 'Fullscreen' INTEGER NOT NULL DEFAULT 0, 'Second View' INTEGER NOT NULL DEFAULT 1, Maximized INTEGER NOT NULL DEFAULT 0);
"""

def main():
    App(info=INFO,
       shortcuts={
        "Posts": {
            "Properties": "<primary>e",
            "Select All": "<primary>a",
            "Favorite": "<primary>d",
            "Download": "<primary>s"
        },
        "Search": {
            "Search": "Return",
            "Search in Background": "<shift>Return",
            "Hide Autocomplete": "Escape",
            "Paste (Files/URI)": "<primary>v",
            "Move Search to Second Bar": "<primary>d"
        },
        "Tabs": {
            "New": "app.new-tab",
            "Close": "app.close-tab",
            "Reopen Closed": "app.reopen-tab",
            "Overview": "app.overview",
            "Move to Second Bar": "app.move-or-fav",
            **Adw.TabView.shortcuts
        },
        "Window": {
            "New": "app.new-window",
            "Open URIs": "app.open-uris",
            "Fullscreen": "F11",
            "Second Bar": "<primary><shift>b"
        },
        "Picture" : Picture.shortcuts,
        "Media Controls": MediaControls.shortcuts,
        "Catalog/Manga/Thread": handle_scroll.shortcuts
       },
       data=DATA_INIT,
       file_open=file_open,
       activate=activate,
       actions=(
        ("open-uris", open_uris, "<primary>o"),
        ("download", download, "<primary>s"),
        ("overview", overview, "<primary><shift>o"),
        ("reopen-tab", reopen_tab, "<primary><shift>t"),
        ("new-window", Window.create, "<primary>n"),
        ("new-tab", Tab.create, "<primary>t"),
        ("move-or-fav", Tab.operation, "<primary>d"),
        ("context-move-or-fav", Tab.operation),
        ("close-tab", Tab.operation, "<primary>w"),
        ("context-close-tab", Tab.operation),))
    App.default.add_action(Gio.SimpleAction.new("context", get_variant("str").get_type()))
    App.default.lookup_action("context").connect("activate", Context.activate)
    App.default.set_accels_for_action("win.fullscreen", ["F11"])
    App.default.set_accels_for_action("win.second-view", ["<primary><shift>b"])
    App.default.data.set_default(table="Boards", conditions="Name = 'Favorites'", values=("Favorites",), names=("Name",))
    App.default.lookup_action("reopen-tab").set_enabled(False)
    Window.menu = Menu({"!a": Menu({"Open URIs": "open-uris"}), "!b": Menu({"Fullscreen": "win.fullscreen", "Second View": "win.second-view", "New Window": "new-window", "View Open Tabs": "overview", "Reopen Closed Tab": "reopen-tab"}), "!c": App.default.default_menu})
    Boards.list.default.get_model().extend(App.default.data.read(table="Boards", return_dict=True, force_tuple=True))
    App.default.main(css=APP_CSS)

if __name__ == "__main__": main()