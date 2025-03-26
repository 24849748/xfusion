import os
from jinja2 import Template
from pathlib import Path

class MDK:
    def __init__(self, name) -> None:
        self.DIR_PROJECT = os.path.dirname(os.path.abspath(name))

        self.ctxIncludePath = []
        self.ctxMiscControls = set()

    def to_project_relpaths(self, path):
        """
        将 path 转换为基于当前路径工程路径的相对路径
        """
        if isinstance(path, Path):
            path = str(path)

        if isinstance(path, str):
            path = os.path.abspath(path)
            result = os.path.relpath(path, self.DIR_PROJECT)
        elif isinstance(path, list):
            result = []
            for i in path:
                i = os.path.abspath(i)
                result.append(os.path.relpath(i, self.DIR_PROJECT))
        return result

    def __get_file_type(self, file_path):
        file_name = os.path.basename(file_path)
        _, file_suffix = os.path.splitext(file_name)
        if file_suffix == ".c":
            file_type = "1"
        elif file_suffix == ".s" or file_suffix == ".S":
            file_type = "2"
        elif file_suffix == ".o":
            file_type = "3"
        elif file_suffix == ".lib":
            file_type = "4"
        elif file_suffix == ".h":
            file_type = "5"
        elif file_suffix == ".cpp" or file_suffix == ".cxx":
            file_type = "8"
        else:
            file_type = "9"
        return file_type

    def __get_file_name(self, file_path):
        return os.path.basename(file_path)

    def __project_info_launch(self, info):
        # 预处理，将 srcs 的结构转换为 js2 能使用的结构
        groups = []
        for GroupName, files in self.info["srcs"].items():
            f = []
            for file in files:
                if not file.strip():
                    continue
                f.append({
                    "name": self.__get_file_name(file),
                    "type": self.__get_file_type(file),
                    "path": file,
                })

            groups.append({
                    "GroupName": GroupName,
                    "Files": f
                })

        info.update({"Groups": groups})

        return info

    def save_uvoptx(self, name):
        pass

    def save_uvprojx(self, name):
        with open("./uvprojx.j2", "r", encoding="utf-8") as file:
            uvprojx_j2 = file.read()

        template = Template(uvprojx_j2)
        info = self.__project_info_launch(self.info)
        print("lanuch", info)
        result = template.render(info)

        with open(name, "w", encoding="utf-8") as file:
            file.write(result)

    def set_target(self, name):
        self.info["project"]["name"] = name

    def set_device(self, device, vendor, packid):
        pack_info = {
            "Device":device,
            "Vendor":vendor,
            "PackID":packid,
        }
        self.info.update({"pack": pack_info})

    def set_startup(self, name):
        self.update_files("core", name)

    def remove_group(self, group):
        self.info["srcs"].pop(group, None)

    def update_files(self, group, files):
        """
        将 group 中原来的文件列表更新为 files 
        """
        if not files:
            return

        files = self.to_project_relpaths(files)

        if isinstance(files, str):
            files = list([files])

        self.info["srcs"].update({group:files})

    def add_include_path(self, paths):
        if not paths:
            return

        paths = self.to_project_relpaths(paths)
        if isinstance(paths, str):
            self.ctxIncludePath.add(paths)
        elif isinstance(paths, list):
            self.ctxIncludePath |= set(paths)

    def remove_include_path(self, paths):
        if not paths:
            return

        paths = self.to_project_relpaths(paths)
        if isinstance(paths, str):
            self.ctxIncludePath.remove(paths)
        elif isinstance(paths, list):
            self.ctxIncludePath -= set(paths)

    def add_MiscControls(self, params):
        if isinstance(params, str):
            self.ctxMiscControls.add(params)
        elif isinstance(params, list):
            self.ctxMiscControls |= set(params)

    def remove_MiscControls(self, params):
        if isinstance(params, str):
            self.ctxMiscControls.remove(params)
        elif isinstance(params, list):
            self.ctxMiscControls -= set(params)

    def set_preinclude(self, path):
        path = self.to_project_relpaths(path)
        text = f"--preinclude={path}"
        self.add_MiscControls(text)

    def set_ScatterFile(self, path:str):
        path = self.to_project_relpaths(path)
        self.info["project"]["sct"] = path
