#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2022-04-21 10:58:46
# @Author  : Your Name (you@example.org)
# @Link    : link
# @Version : 1.0.0

import base64
import json
import os
import pprint
import socket
import sys
from dataclasses import dataclass
from io import BytesIO, StringIO
import threading

import dotenv
import envlibloader
import PIL.Image
import pystray
import PySimpleGUI as sg
import utils


class Launcher:

    def __init__(self):
        self.treedata = sg.TreeData()
        self.title = os.path.basename(os.path.dirname(sys.argv[0]))
        self.window = None
        self.tree = None
        self.systray = None

    @dataclass
    class TreeAppItem:

        def __init__(self, *args):
            if len(args) == 1:
                if type(args[0]) == dict:
                    return self._from_dict(args[0])
                else:
                    self.exe_path = args[0]
            elif len(args) == 3:
                self.exe_path = args[0]
                self.title = args[1] if args[1] is not None else os.path.basename(
                    self.exe_path)
                self.env_ini = args[2]

        def _from_dict(self, dict_item):
            return self.__init__(dict_item['exe_path'], dict_item['title'], dict_item['env_ini'])

        def serialize(self):
            return self.__dict__

        def __str__(self) -> str:
            return self.__dict__.__str__()

    class TreeAppItemEncoder(json.JSONEncoder):
        def default(self, treeappitem):
            if isinstance(treeappitem, Launcher.TreeAppItem):
                return treeappitem.serialize()

    def _search_treedata(self, treedata, q):
        selected = []
        for item in self.treedata.tree_dict.values():
            if item.text.find(q) >= 0:
                selected.append(item.text)
        return selected

    def _add_exe_to_tree(self, treedata, *args):
        treeappitem = None
        if type(args[0]) == Launcher.TreeAppItem:
            treeappitem = args[0]
        else:
            treeappitem = Launcher.TreeAppItem(*args)
        iconpngbytes = utils.get_exe_icon(treeappitem.exe_path)
        treeappitem.tmpicon = utils.tmpicon(utils.get_icon_as_icobytes(treeappitem.exe_path))
        if len(treeappitem.exe_path) > 0 or treeappitem.exe_path.endswith('.exe'):
            treedata.insert('', key=treeappitem.exe_path, text=treeappitem.title, values=[
                            treeappitem], icon=iconpngbytes)
        else:
            sg.popup_error(
                f"A filepath for a non-exe : '{treeappitem.exe_path}' was passed!")

    def _copy_tree(self, treedata):
        new_treedata = sg.TreeData()
        for item in treedata.tree_dict.values():
            new_treedata.insert('', key=item.key, text=item.text,
                                values=item.values, icon=item.icon)
        return new_treedata

    def _make_treedata_from_dict(self, treedata_dict):
        new_treedata = sg.TreeData()
        for item in treedata_dict.values():
            if item.key != '':
                new_treedata.insert(
                    '', key=item.key, text=item.text, values=item.values, icon=item.icon)
        return new_treedata

    def _fetch_base64_img(self, im_b64):
        im_bytes = base64.b64decode(im_b64)   # im_bytes is a binary image
        im_file = BytesIO(im_bytes)  # convert image to file-like object
        return im_file

    def _extract_dict_from_treedata(self, treedata):
        dict_tree = dict(treedata.tree_dict)
        aux_dict = {}
        for key in dict_tree.keys():
            if len(key) > 0:
                node_title = dict_tree[key].text
                node_value = dict_tree[key].values[0]
                aux_dict[node_title] = node_value
        return aux_dict

    def _properties_window(self, exefilepath):
        pprint.pprint(exefilepath)

    def _save_tree(self, treedata):
        dict_tree = self._extract_dict_from_treedata(treedata)
        json.dump(dict_tree, open(self._get_json_tree_file(), 'w'),
                  indent=4, cls=Launcher.TreeAppItemEncoder)
        # sg.popup_ok(f'Tree saved to {self._get_json_tree_file()}!')

    def _reconstruct_tree(self, treedata):
        self._rebuild_tree_from_file(treedata, self._get_json_tree_file())

    def _rebuild_tree_from_file(self, treedata, jsontreefile):
        read_tree = json.load(open(jsontreefile, 'r'))
        for key, value in read_tree.items():
            new_entry = Launcher.TreeAppItem(value)
            self._add_exe_to_tree(treedata, new_entry)
        return treedata

    def _init_window(self):

        if not os.path.exists(self._get_json_tree_file()):
            print("Creating new tree file " +
                  os.path.abspath(self._get_json_tree_file()))
            f = open(self._get_json_tree_file(), 'w')
            f.write('{}')
            f.close()

        self._reconstruct_tree(self.treedata)

        self.tree = sg.Tree(data=self.treedata,
                            headings=[],
                            auto_size_columns=True,
                            select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                            key='-TREE-',
                            num_rows=15,
                            col0_width=20,
                            show_expanded=False,
                            enable_events=True,
                            expand_x=True,
                            right_click_menu=[
                                'Menu', ['&Add', '&Delete', '&Edit']],
                            expand_y=True
                            )

        print("treedata", self.tree.TreeData)

        layout = [
            [sg.Menu([['&File', ['&Open', '&Save', '&Edit', 'E&xit', ]], [
                     '&Help', ['&About']]], key='-MENU-')],
            [self.tree]
        ]
        self.window = sg.Window(
            self.title, layout, resizable=False, finalize=True, icon='app-menu-launcher.ico')

        self._init_systray()

        self.window.bind('<Button-2>', 'middle_click')
        self.window.bind('<Double-Button-1>', 'double_click')
        self.window.bind('<Button-3>', 'right_click')

    def _send_to_tray(self, systray, menu_item):
        # Benefitting from the hack, we can access the exe_path attribute
        self.window.write_event_value('double_click', menu_item.exe_path)

    def _systray_exec(self,systray,node):
        self.window.write_event_value('double_click', node.exe_path)

    def _regenerate_tray_menu(self):
        treeitems = dict(self.treedata.tree_dict)
        menuitems = []
        for item in treeitems.values():
            if len(item.values) > 0:
                node = item.values[0]
                newmenuitem = pystray.MenuItem(
                    text=node.title, icon=utils.get_exe_img(node.exe_path),action=lambda systray, this_menu_item: self._send_to_tray(
                        systray, this_menu_item)
                )
                # this is a hack: assigning a non-defined attribute in the class MenuItem
                newmenuitem.exe_path = node.exe_path
                menuitems.append(newmenuitem)

        menuitems.extend((pystray.Menu.SEPARATOR,
                          pystray.MenuItem(
                              'About', (lambda: self.window.write_event_value('About', None))),
                          pystray.MenuItem(
                              'Exit', (lambda: self.window.write_event_value('Exit', None))),
                          )
                         )

        return pystray.Menu(lambda: menuitems)                         

    def _init_systray(self):


        self.systray = pystray.Icon(self.title, icon=PIL.Image.open('app-menu-launcher.ico'),
                                    menu= self._regenerate_tray_menu()
                                    )
        self.systray.menuitems = self.systray.menu.items
       
        return self.systray

    def _reset_systray(self):
        self.systray.menu = self._regenerate_tray_menu()
        self.systray.update_menu()

    def _systray_event_loop(self):
        self.systray.run() #using pystrary


    def exit(self,systray=None):
        self.systray.stop()
        print("Exiting", self.systray)
        self.window.close()
 
    def _edit_item_window(self, window_title: str, node):
        return sg.Window(window_title,

                         layout=[[sg.Image(node.icon, size=(32, 32), k='icon')],
                                 [sg.Text('Title'), sg.Input(
                                     node.text, k='title_input')],
                                 [sg.Text('Path'), sg.InputText(node.values[0].exe_path if len(node.values) > 0 else '', k='path_input', enable_events=True),
                                 sg.FileBrowse(enable_events=True, target='path_input',
                                               k='path_browser', file_types=(("Executables", "*.exe"),)
                                               )],
                                 [sg.Text('Env ini'), sg.Input(node.values[0].env_ini if hasattr(node.values[0], 'env_ini') else '', k='env_ini_input', enable_events=True),
                                 sg.FileBrowse(enable_events=True, target='env_ini_input', k='env_ini_browser', file_types=(("Ini files", "*.ini"), ("Env files", "*.env")))],
                                 [sg.OK(), sg.Cancel()]
                                 ], resizable=False,
                         modal=True,
                         finalize=True
                         )

    def replace_icon(self, icondata):
        byte_file = BytesIO(icondata)
        icon = PIL.Image.open(byte_file)
        resized = icon.resize((32, 32), PIL.Image.LANCZOS)

        resized_bytes = BytesIO()
        resized.save(resized_bytes, format='PNG')
        resized.close()
        return resized_bytes

    def _get_json_tree_file(self):
        portable_drive = utils.is_running_in_portable_drive()
        if portable_drive != False:
            volume_name = utils.get_volume_name(portable_drive)
            return 'tree.' + volume_name + '.json'
        return 'tree.' + socket.gethostname() + '.json'

    def _about_window(self):
        sg.Window('About', [[sg.Text('''
        AppMenuLauncher 0.1.0, 2023, by digfish
        https://me.digfish.org
        sam@digfish.org
        ''')], [sg.OK()]], modal=True).read(close=True)

    def _launch_exe(self, exefilepath):
        import subprocess
        if sys.platform == 'darwin':
            subprocess.call(['open', exefilepath])
        else:
            # opener ="open" if sys.platform == "darwin" else "xdg-open"
            # subprocess.call(['open', exefilepath])
            subprocess.Popen([exefilepath], env=os.environ)

    def window_loop(self):
        self.window.perform_long_operation(self._systray_event_loop,None)
        #self.systray.start()
        # print('last_message',self.systray.last_message_event)
        while True:
            self.treedata = self.tree.TreeData
            event, values = self.window.read()
            # window, event, values = sg.read_all_windows()
            # print(window, event, values)
            print(event, values)
            if event in (sg.WIN_CLOSED, 'Exit'):
                self._save_tree(self.tree.TreeData)
                break
            elif event == '-TREE-':
                if len(values['-TREE-']) > 0:
                    node_value = values['-TREE-'][0]
            elif event == 'double_click':  # execute item
                chosen_node_key = values['-TREE-'][0] if len(
                    values['-TREE-']) > 0 else values['double_click']
                chosen_node = self.treedata.tree_dict[chosen_node_key].values[0]
                exe_path = chosen_node.exe_path
                env_ini: str = chosen_node.env_ini
                exefilename = os.path.basename(exe_path)
                if utils.is_process_running(exefilename):
                    print(f"Process {exefilename} is already running!")
                    answer = sg.popup_yes_no(
                        f'{exefilename} is already running, kill it?', title='Kill process?')
                    print(f"Answer: {answer}")
                    if answer == 'Yes':
                        print("Terminating process...")
                        utils.kill_by_name(exefilename)
                        print("DONE!")
                if env_ini is not None:
                    if env_ini.endswith('.ini'):
                        envlibloader.set_env_vars(env_ini)
                    elif env_ini.endswith('.env'):
                        dotenv.load_dotenv(env_ini, override=True)
                print(f"Launcing {exe_path}")
                self._launch_exe(exe_path)
            elif event == 'right_click':
                if len(values['-TREE-']) > 0:
                    exefilepath = values['-TREE-'][0]
                    # properties_window(exefilepath)
            elif event == 'Open':
                jsontreefile = sg.popup_get_file(
                    'Open menu json definition', file_types=(("JSON Files", "*.json"),))
                if jsontreefile is not None:
                    newtreedata = self._rebuild_tree_from_file(
                        sg.TreeData(), jsontreefile)
                    self.tree.update(values=newtreedata)
                    self.treedata = self.tree.TreeData
                    self._reset_systray()

            elif event == 'Edit':
                if len(values['-TREE-']) > 0:
                    curr_exefilepath = values['-TREE-'][0]
                    curr_title = self.treedata.tree_dict[curr_exefilepath].values[0].title

                    current_node_keys = list(
                        self.tree.TreeData.tree_dict.keys())
                    env_ini_path = self.tree.TreeData.tree_dict[curr_exefilepath].values[0].env_ini
                    icondata = self.tree.TreeData.tree_dict[curr_exefilepath].icon
                    resized_bytes = self.replace_icon(icondata)

                    prop_win = self._edit_item_window(
                        'Edit item', self.tree.TreeData.tree_dict[curr_exefilepath])

                    while True:
                        (event, values) = prop_win.read()
                        print(event, values)
                        # sg.Popup(event,values)
                        if event == 'path_input':
                            exefilepath = values['path_input']
                            icondata = utils.get_exe_icon(exefilepath)
                            resized_bytes = self.replace_icon(icondata)
                            prop_win['title_input'].update(
                                value=os.path.splitext(os.path.basename(exefilepath))[0])
                            prop_win['icon'].update(
                                data=resized_bytes.getvalue())
                        elif event == 'env_ini_input':
                            env_ini_path = values['env_ini_input']
                        elif event == 'OK':
                            exefilepath = values['path_input']
                            new_title = values['title_input']
                            new_env_ini = values['env_ini_input']
                            cur_idx = current_node_keys.index(curr_exefilepath)
                            current_node_keys[cur_idx] = exefilepath
                            new_tree_data = sg.TreeData()
                            for filexe_key in current_node_keys:
                                if len(filexe_key) > 0:
                                    if filexe_key == exefilepath:
                                        title = new_title
                                        env_ini = new_env_ini
                                    else:
                                        existing_node = self.treedata.tree_dict[filexe_key]
                                        title = existing_node.values[0].title
                                        env_ini = existing_node.values[0].env_ini
                                    self._add_exe_to_tree(
                                        new_tree_data, filexe_key, title, env_ini)
                            self.tree.update(values=new_tree_data)
                            self.treedata = self.tree.TreeData

                            self._reset_systray()
                            break
                        elif event == 'Cancel':
                            break
                    prop_win.close()
            elif event == 'Add':
                selected_key = None
                if len(values['-TREE-']) > 0:
                    selected_key = values['-TREE-'][0]

                winbrowse = self._edit_item_window("Add new executable", sg.TreeData.Node(
                    '', key='', icon=utils.get_exe_icon(''), text='', values=[Launcher.TreeAppItem('')]))
                while True:
                    event, values = winbrowse.read()

                    print(event, values)
                    exe = values['path_input']
                    new_title = values['title_input']
                    new_env_ini_path = values['env_ini_input']
                    if len(new_title.strip()) == 0:
                        new_title = os.path.splitext(os.path.basename(exe))[0]
                    elif event == 'env_ini_input':
                        env_ini_path = values['env_ini_input']
                    if event == 'path_input':
                        exefilepath = values['path_input']
                        icondata = utils.get_exe_icon(exefilepath)
                        resized_bytes = self.replace_icon(icondata)
                        winbrowse['title_input'].update(value=new_title)
                        winbrowse['icon'].update(data=resized_bytes.getvalue())

                    elif event == 'OK':
                        if selected_key is not None:  # if a node is selected, insert after it
                            current_node_keys = list(
                                self.tree.TreeData.tree_dict.keys())
                            cur_idx = current_node_keys.index(selected_key)
                            current_node_keys.insert(cur_idx+1, exe)
                            new_tree_data = sg.TreeData()
                            for exename_key in current_node_keys:
                                if len(exename_key) > 0:
                                    title = new_title
                                    env_ini_path = new_env_ini_path
                                    if exename_key != exe:
                                        current_node = self.treedata.tree_dict[exename_key]
                                        title = current_node.values[0].title
                                        env_ini_path = current_node.values[0].env_ini
                                    self._add_exe_to_tree(
                                        new_tree_data, exename_key, title, env_ini_path)
                            self.tree.update(values=new_tree_data)
                            self.treedata = self.tree.TreeData
                            self._reset_systray()
                        else:  # no node selected, append to the end
                            self._add_exe_to_tree(
                                self.tree.TreeData, exe, new_title, new_env_ini_path)
                            self.tree.update(values=self.tree.TreeData)
                            self.treedata = self.tree.TreeData
                            self._reset_systray()
                        break
                    elif event == 'Cancel':
                        break
                winbrowse.close()
            elif event == 'Delete':
                if len(values['-TREE-']) > 0:
                    exefilepath = values['-TREE-'][0]
                    answer = sg.PopupYesNo(
                        'Are you sure you want to remove this item?')
                    print(answer)
                    if answer == 'Yes':
                        treedata_dict = dict(self.tree.TreeData.tree_dict)
                        del (treedata_dict[exefilepath])
                        new_treedata = self._make_treedata_from_dict(
                            treedata_dict)
                        self.tree.update(values=new_treedata)
                        self.treedata = self.tree.TreeData
                        self._reset_systray()

            elif event == 'Save':
                print("Saving tree!")
                self._save_tree(self.tree.TreeData)
            elif event == 'About':
                self._about_window()
            else:
                continue

        self.exit()


def main():
    launcher = Launcher()
    launcher._init_window()
    launcher.window_loop()


if __name__ == '__main__':
    main()
