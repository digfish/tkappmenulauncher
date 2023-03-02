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
from io import BytesIO, StringIO
import PIL.Image
import PySimpleGUI as sg
import utils
from dataclasses import dataclass
import envlibloader

class Launcher:

    def __init__(self):
        self.treedata = sg.TreeData()
        self.title = sys.argv[0]
        self.window = None
        self.tree = None

    @dataclass
    class TreeAppItem:

        def __init__(self,exe_path=None,title=None):
            self.exe_path = exe_path
            self.title = title if title is not None else os.path.basename(exe_path)

        def serialize(self):
            return self.__dict__
        
        def __str__(self) -> str:
            return self.__dict__.__str__()
        
    class TreeAppItemEncoder(json.JSONEncoder):
        def default(self,treeappitem):
            if isinstance(treeappitem,Launcher.TreeAppItem):
                return treeappitem.serialize()


    def _search_treedata(self,treedata,q):
        selected = []
        for item in self.treedata.tree_dict.values():
            if item.text.find(q) >= 0:
                selected.append(item.text)
        return selected

    def _add_exe_to_tree(self,treedata,exe_path,title=None):
        if len(exe_path) > 0 or exe_path.endswith('.exe'):
            treedata.insert('', key=exe_path, text=title, values=[
                            Launcher.TreeAppItem(exe_path, title)], icon=utils.get_exe_icon(exe_path))
        else:
            sg.popup_error(f"A filepath for a non-exe : '{exe_path}' was passed!")

    def _copy_tree(self,treedata):
        new_treedata = sg.TreeData()
        for item in treedata.tree_dict.values():
            new_treedata.insert('',key=item.key,text=item.text,values=item.values,icon=item.icon)
        return new_treedata

    def _make_treedata_from_dict(self,treedata_dict):
        new_treedata = sg.TreeData()
        for item in treedata_dict.values():
            if item.key != '':
                new_treedata.insert('',key=item.key,text=item.text,values=item.values,icon=item.icon)
        return new_treedata

    def _fetch_base64_img(self,im_b64):
        im_bytes = base64.b64decode(im_b64)   # im_bytes is a binary image
        im_file = BytesIO(im_bytes)  # convert image to file-like object
        return im_file

    def _extract_dict_from_treedata(self,treedata):
        dict_tree = dict(treedata.tree_dict)
        aux_dict = {}
        for key in dict_tree.keys():
            if len(key) > 0:
                node_title = dict_tree[key].text
                node_value = dict_tree[key].values[0]
                aux_dict[node_title] =   node_value 
        return aux_dict

    def _properties_window(self,exefilepath):
        pprint.pprint(exefilepath)

    def _save_tree(self,treedata):
        dict_tree = self._extract_dict_from_treedata(treedata)
        json.dump(dict_tree,open(self._get_json_tree_file(),'w'),indent=4,cls=Launcher.TreeAppItemEncoder)
        sg.popup_ok(f'Tree saved to {self._get_json_tree_file()}!')

    def _reconstruct_tree(self,treedata):
        self._rebuild_tree_from_file(treedata, self._get_json_tree_file())

    def _rebuild_tree_from_file(self, treedata, jsontreefile):
        read_tree = json.load(open(jsontreefile,'r'))
        for key, value in read_tree.items():
            self._add_exe_to_tree(treedata,value['exe_path'],value['title'])
        return treedata

    def _init_window(self):
        self._reconstruct_tree(self.treedata)

        self.tree = sg.Tree(data=self.treedata,
                        headings = [],
                        auto_size_columns=True,
                        select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                        key='-TREE-',
                        num_rows=15,
                        col0_width=20,
                        show_expanded=False,
                        enable_events=True,
                        expand_x=True,
                        right_click_menu=['Menu',['&Add','&Delete','&Edit']],
                        expand_y=True,
        )



        print("treedata",self.tree.TreeData)



        layout = [
            [sg.Menu([['&File', ['&Open', '&Save', '&Edit', 'E&xit', ]],['&Help',['&About']]], key='-MENU-')],
            [self.tree]
        ]
        self.window = sg.Window(self.title,layout,resizable=False, finalize=True)

        self.window.bind('<Button-2>', 'middle_click')
        self.window.bind('<Double-Button-1>','double_click')
        self.window.bind('<Button-3>', 'right_click')

    def _edit_item_window(self,window_title:str,node):
        return sg.Window(window_title,

                        layout=[[sg.Image(node.icon, size=(32,32),k='icon')],
                                [sg.Text('Title'),sg.Input(node.text,k='title_input')],
                                [sg.Text('Path'),sg.InputText(node.values[0].exe_path if len(node.values) > 0 else '',k='path_input',enable_events=True),
                                sg.FileBrowse(enable_events=True, target='path_input',
                                                k='path_browser',file_types=(("Executables", "*.exe"),)
                                )],
                                [sg.OK(),sg.Cancel()]
                        ],resizable=False,
                        modal=True,
                        finalize=True
        )


    def replace_icon(self,icondata):
        byte_file = BytesIO(icondata)
        icon = PIL.Image.open(byte_file )
        resized = icon.resize((32,32),PIL.Image.LANCZOS)

        resized_bytes = BytesIO()
        resized.save(resized_bytes,format='PNG')
        resized.close()
        return resized_bytes
    
    def _get_json_tree_file(self):
        return 'tree.'+ socket.gethostname() +'.json'

    def _about_window(self):
        sg.Window('About',[[sg.Text('''
        AppMenuLauncher 0.1.0, 2023, by digfish
        https://me.digfish.org
        sam@digfish.org
        ''')],[sg.OK()]]).read(close=True)


    def window_loop(self):
        while True:
            self.treedata = self.tree.TreeData
            event, values = self.window.read()
            print(event, values)
            if event in (sg.WIN_CLOSED,'Exit'):
                self._save_tree(self.tree.TreeData)
                break
            elif event == '-TREE-':
                if len(values['-TREE-']) > 0:
                    node_value = values['-TREE-'][0]
            elif event == 'double_click':
                exefilepath = values['-TREE-'][0]
                os.startfile(exefilepath)
            elif event == 'right_click':
                if len(values['-TREE-']) > 0:
                    exefilepath = values['-TREE-'][0]
                    #properties_window(exefilepath)
            elif event == 'Open':
                jsontreefile = sg.popup_get_file('Open menu json definition',file_types=(("JSON Files", "*.json"),))
                if jsontreefile is not None:
                    newtreedata = self._rebuild_tree_from_file(sg.TreeData(),jsontreefile)
                    self.tree.update(values=newtreedata)

            elif event == 'Edit':
                if len(values['-TREE-']) > 0:
                    curr_exefilepath = values['-TREE-'][0]
                    curr_title = self.treedata.tree_dict[curr_exefilepath].values[0].title

                    current_node_keys = list(self.tree.TreeData.tree_dict.keys())

                    icondata = self.tree.TreeData.tree_dict[curr_exefilepath].icon
                    resized_bytes = self.replace_icon(icondata)

                    prop_win = self._edit_item_window('Edit item',self.tree.TreeData.tree_dict[curr_exefilepath])

                    while True:
                        (event,values) = prop_win.read()
                        print(event,values)
                        #sg.Popup(event,values)
                        if event == 'path_input':
                            exefilepath = values['path_input']
                            icondata = utils.get_exe_icon(exefilepath)
                            resized_bytes = self.replace_icon(icondata)
                            prop_win['title_input'].update(value=os.path.splitext(os.path.basename(exefilepath))[0])
                            prop_win['icon'].update(data=resized_bytes.getvalue())
                        elif event == 'OK':
                            exefilepath = values['path_input']
                            title = values['title_input']
                            cur_idx = current_node_keys.index(curr_exefilepath)
                            current_node_keys[cur_idx] = exefilepath
                            new_tree_data = sg.TreeData()
                            for filexe_key in current_node_keys:
                                if len(filexe_key) > 0:
                                    if filexe_key == exefilepath:
                                        existing_title = title
                                    else:
                                        existing_node = self.treedata.tree_dict[filexe_key]
                                        existing_title = existing_node.values[0].title
                                    self._add_exe_to_tree (new_tree_data,filexe_key,existing_title)
                            self.tree.update(values=new_tree_data)
                            break
                        elif event == 'Cancel':
                            break
                    prop_win.close()
            elif event == 'Add':
                selected_key = None
                if len(values['-TREE-']) > 0:
                    selected_key = values['-TREE-'][0]
                    
                winbrowse = self._edit_item_window("Add new executable",sg.TreeData.Node('',key='',icon=utils.get_exe_icon(''),text='',values=[Launcher.TreeAppItem('')]))
                while True:
                    event,values = winbrowse.read()

                    print(event,values)
                    exe = values['path_input']
                    title = values['title_input']
                    if len(title.strip()) == 0:
                        title = os.path.splitext(os.path.basename(exe))[0]
                    if event == 'path_input':
                        exefilepath = values['path_input']
                        icondata = utils.get_exe_icon(exefilepath)
                        resized_bytes = self.replace_icon(icondata)
                        winbrowse['title_input'].update(value=title)
                        winbrowse['icon'].update(data=resized_bytes.getvalue())

                    elif event == 'OK':
                        if selected_key is not None: #if a node is selected, insert after it
                            current_node_keys = list(self.tree.TreeData.tree_dict.keys())
                            cur_idx = current_node_keys.index(selected_key)
                            current_node_keys.insert(cur_idx+1,exe)
                            new_tree_data = sg.TreeData()
                            for exename_key in current_node_keys:
                                if len(exename_key) > 0:
                                    if exename_key == exe:
                                        current_title = title
                                    else:
                                        current_node = self.treedata.tree_dict[exename_key]
                                        current_title = current_node.values[0].title
                                    self._add_exe_to_tree(
                                        new_tree_data, exename_key, current_title)
                            self.tree.update(values=new_tree_data)
                        else: # no node selected, append to the end
                            self._add_exe_to_tree(self.tree.TreeData,exe,title)
                            self.tree.update(values=self.tree.TreeData)
                        break
                    elif event == 'Cancel':
                        break
                winbrowse.close()
            elif event == 'Delete':
                if len(values['-TREE-']) > 0:
                    exefilepath = values['-TREE-'][0]
                    answer = sg.PopupYesNo('Are you sure you want to remove this item?')
                    print(answer)
                    if answer == 'Yes':
                        treedata_dict = dict(self.tree.TreeData.tree_dict)
                        del(treedata_dict[exefilepath])
                        new_treedata =self._make_treedata_from_dict(treedata_dict)
                        self.tree.update(values=new_treedata)
            elif event == 'Save':
                print("Saving tree!")
                self._save_tree(self.tree.TreeData)
            elif event == 'About':
                self._about_window()
            else: continue
        self.window.close()



def main():
    launcher = Launcher()
    launcher._init_window()
    launcher.window_loop()


if __name__ == '__main__':
    main()

