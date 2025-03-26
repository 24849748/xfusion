import os
from jinja2 import Template
from pathlib import Path
import json

class MDK:
    info = {
        "project": {
            "name":"",
            "sct":"",
        },
        "pack": {
            "Device":"",
            "Vendor":"",
            "PackID":"",
        },
        "program": {},
        "MiscControls": [
            "--C99",
            "--gnu",
            "--thumb",
            "--diag_suppress=1",
            "--bss_threshold=0"
        ],
        "Define":[],
        "IncludePath": [],
        # 这种结构方便使用 dict update
        "srcs":{
            "core":[".\\startup.s"],
        },
    }

    def __init__(self, name, path_js2, last_info=None) -> None:
        self.DIR_PROJECT = os.path.dirname(os.path.abspath(name))
        if last_info:
            self.info = last_info 
        self.path_uvoptx_js2 = Path(path_js2) / "uvoptx.j2"
        self.path_uvprojx_js2 = Path(path_js2) / "uvprojx.j2"

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
        info = self.info.copy()
        groups = []
        for GroupName, files in info["srcs"].items():
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

    def save_info(self, name):
        with open(name, "w", encoding="utf-8") as f:
            json.dump(self.info, f, indent=4)

    def save_uvoptx(self, name):
        with open(self.path_uvoptx_js2, "r", encoding="utf-8") as file:
            uvoptx_j2 = file.read()

        template = Template(uvoptx_j2)
        info = self.__project_info_launch(self.info)
        result = template.render(info)

        with open(name, "w", encoding="utf-8") as file:
            file.write(result)

    def save_uvprojx(self, name):
        self.info["IncludePath"] = list(set(self.info["IncludePath"]))
        with open(self.path_uvprojx_js2, "r", encoding="utf-8") as file:
            uvprojx_j2 = file.read()

        template = Template(uvprojx_j2)
        info = self.__project_info_launch(self.info)
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

    def set_sw_param(self, algo_start:str, algo_size:str,
                     flm_path:str, flm_start:str, flm_size:str):
        def hex_prepare(value):
            """ 去除 0x 及 多余的 0 """
            return value.lstrip("0x").lstrip("0") or "0"
        flm_name = os.path.basename(flm_path).split(".")[0]
        program_info = {
            "algo_start":hex_prepare(algo_start),
            "algo_size": hex_prepare(algo_size),
            "flm_name": flm_name,
            "flm_path": flm_path,
            "flm_start": hex_prepare(flm_start),
            "flm_size": hex_prepare(flm_size),
        }
        self.info.update({"program":program_info})

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
            self.info["IncludePath"].append(paths)
        elif isinstance(paths, list):
            self.info["IncludePath"] += paths

    def remove_include_path(self, paths):
        if not paths:
            return

        paths = self.to_project_relpaths(paths)
        if isinstance(paths, str):
            if paths in self.info["IncludePath"]:
                self.info["IncludePath"].remove(paths)
        elif isinstance(paths, list):
            for v in paths:
                if v in self.info["IncludePath"]:
                    self.info["IncludePath"].remove(v)

    def add_MiscControls(self, params):
        if isinstance(params, str):
            self.info["MiscControls"].append(params)
        elif isinstance(params, list):
            self.info["MiscControls"] += params

    def remove_MiscControls(self, params):
        if isinstance(params, str):
            self.info["MiscControls"].remove(params)
        elif isinstance(params, list):
            for v in params:
                if v in self.info["MiscControls"]:
                    self.info["MiscControls"].remove(v)

    def set_preinclude(self, path):
        path = self.to_project_relpaths(path)
        text = f"--preinclude={path}"
        self.add_MiscControls(text)

    def set_ScatterFile(self, path:str):
        path = self.to_project_relpaths(path)
        self.info["project"]["sct"] = path
