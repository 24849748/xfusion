import xf_build
from xf_build import api
import shutil
import json
from .FileChange import FileChange
from .mdk import MDK
from os.path import relpath
import os
from os.path import join
from pathlib import Path
import logging

from rich import print

hookimpl = xf_build.get_hookimpl()

def user_collect(path:Path, 
                 srcs: list = ["*.c"], 
                 inc_dirs: list = ["."]):
    def deep_flatte(iterable):
            result = []
            stack = [iter(iterable)]

            while stack:
                current = stack[-1]
                try:
                    item = next(current)
                    if isinstance(item, list):
                        stack.append(iter(item))
                    else:
                        result.append(item)
                except StopIteration:
                    stack.pop()

            return result

    srcs = [list(path.glob(i)) for i in srcs]
    srcs = deep_flatte(srcs)
    srcs = [i.as_posix() for i in srcs]
    inc_dirs = [(path / i).resolve().as_posix() for i in inc_dirs]

    dict_build_env = {}
    dict_build_env["path"] = path.as_posix()
    dict_build_env["srcs"] = srcs
    dict_build_env["inc_dirs"] = inc_dirs

    return dict_build_env

def collect_srcs(dir_ports):
    srcs = []
    for root, _, files in os.walk(dir_ports):
        for file in files:
            if file.endswith(".c"):
                srcs.append(root+"/"+file)
    return srcs

def change_path_base(base_path, change_path, path):
    """
    将 path 中的 base_path 路径替换为 change_path 路径
    """
    base_path = Path(base_path)
    change_path = Path(change_path)
    replace_path = []

    for _path in path:
        _path = Path(_path)
        # 获取 path 相对于 base_path 的相对路径，如果路径不在 base_path 下，跳过该路径
        try:
            rel_path = _path.relative_to(base_path)
        except ValueError:
            continue

        # 拼接新的路径
        if str(rel_path) == ".":
            # 如果相对路径为空（即 "."），直接使用 change_path
            new_path = change_path
        else:
            new_path = change_path / rel_path
        replace_path.append(str(new_path))

    return replace_path

class pt3210():
    def update_component(self, uvprojx:MDK, key, value, copy_path_base=None):
        """
        增量更新基础组件
        """

        # 需要拷贝到本地的
        if copy_path_base is not None:
            _path = Path(copy_path_base) / key
            if _path.exists():
                shutil.rmtree(_path)
            shutil.copytree(value["path"], _path, dirs_exist_ok=True)
            value["srcs"] = change_path_base(value["path"], _path, value["srcs"])
            value["inc_dirs"] = change_path_base(value["path"], _path, value["inc_dirs"])

        uvprojx.update_files(key, value["srcs"])
        uvprojx.add_include_path(value["inc_dirs"])

    def update_platform(self, uvprojx:MDK, dir_platform_ble, last_info:dict={}):
        """
        只跟踪 menuconfig 配置的变化，不跟踪文件夹内容变化
        """

        ble_enable = False
        use_litelib = False
        if api.get_define("PORT_BLE_ENABLE") == "y":
            ble_enable = True
            if api.get_define("PORT_BLE_CAPABILITY_1C_M_S") == "y":
                brief = "use ble.lib, 1 connection, master or slave"
                name_ble_lib = "ble6.lib"
            elif api.get_define("PORT_BLE_CAPABILITY_3C_M_S") == "y":
                brief = "use ble.lib, 3 connections, master or slave"
                name_ble_lib = "ble6.lib"
            elif api.get_define("PORT_BLE_CAPABILITY_1C_S") == "y":
                brief = "use blelite.lib, 1 connection, only slave"
                name_ble_lib = "ble6_lite.lib"
                use_litelib = True
        else:
            ble_enable = False
            use_litelib = False
            brief = "without ble"

        if last_info.get("brief") != brief:
            # 有变化
            if ble_enable:
                uvprojx.set_blelib((dir_platform_ble / "lib" / name_ble_lib).as_posix())
                uvprojx.add_include_path((dir_platform_ble / "api").as_posix())
                uvprojx.add_include_path((dir_platform_ble / "prf").as_posix())
            else:
                uvprojx.remove_group("ble")
                uvprojx.remove_include_path((dir_platform_ble / "api").as_posix())
                uvprojx.remove_include_path((dir_platform_ble / "prf").as_posix())

            _path = (self.DIR_PROJECT / "link_xip.sct").as_posix()
            self.gen_sct_file(_path, brief, ble_enable, use_litelib)
            uvprojx.set_ScatterFile(_path)

        return {"platform":{"brief": brief}}

    @hookimpl
    def build(self, args):
        logging.error("pt3210 当前不支持 xf build 命令!")

    @hookimpl
    def clean(self, args):
        logging.error("pt3210 当前不支持 xf clean 命令!")

    @hookimpl
    def flash(self, args):
        logging.error("pt3210 当前不支持 xf flash 命令!")

    @hookimpl
    def export(self, name, args):
        if name is None:
            return
        name = Path(name)

        self.PROJECT_NAME = os.path.basename(name)
        self.DIR_PROJECT = api.XF_PROJECT_PATH / self.PROJECT_NAME
        self.PATH_UVPROJX = self.DIR_PROJECT / f"{self.PROJECT_NAME}.uvprojx"
        self.PATH_BUILD_ENV = api.XF_PROJECT_PATH / "build/build_environ.json"

        fc = FileChange(self.PATH_BUILD_ENV)
        # 平台 sdk
        ## 拷贝 project/template 目录到当前工作区
        shutil.copytree(api.XF_TARGET_PATH / "project", 
                        self.DIR_PROJECT, 
                        dirs_exist_ok=True)

        ## 重命名 uvprojx
        os.rename(self.DIR_PROJECT / "template.uvprojx", self.PATH_UVPROJX)

        uvprojx = MDK(self.PATH_UVPROJX)
        uvprojx.set_target(self.PROJECT_NAME)
        uvprojx.set_preinclude(api.XF_PROJECT_PATH / "build/header_config/xfconfig.h")

        ## 拷贝 platform 目录
        DIR_PLATFORM_WORKSPACE = api.XF_PROJECT_PATH / "platform"
        shutil.copytree(api.XF_TARGET_PATH / "platform", 
                        DIR_PLATFORM_WORKSPACE, 
                        dirs_exist_ok=True)

        srcs_platform = [
            "./drvs/src/*.c",
            "./main.c"
        ]
        incs_platform = [
            "core/",
            "core/reg/",
            "drvs/includes/"
        ]
        dict_platform = user_collect(DIR_PLATFORM_WORKSPACE, srcs_platform, incs_platform)
        key = "platform"
        self.update_component(uvprojx, key, dict_platform)
        fc.update_custom_md5(key, DIR_PLATFORM_WORKSPACE.as_posix())
        logging.info(f"{key} 部分导出完成")

        with open(self.PATH_BUILD_ENV, "r") as f:
            build_env = json.load(f)

        # user_main
        key = "user_main"
        self.update_component(uvprojx, key, build_env[key])
        fc.update_component_md5(key)
        logging.info(f"{key} 部分导出完成")

        # user_components
        group_name = "user_components"
        for key, value in build_env[group_name].items():
            self.update_component(uvprojx, key, value)
            fc.update_component_md5(key, group_name)
            logging.info(f"{key} 部分导出完成")

        # user_dirs
        group_name = "user_dirs"
        for key, value in build_env[group_name].items():
            self.update_component(uvprojx, key, value)
            fc.update_component_md5(key, group_name)
            logging.info(f"{key} 部分导出完成")

        # public_components
        group_name = "public_components"
        for key, value in build_env[group_name].items():
            self.update_component(uvprojx, key, value,
                                  copy_path_base = api.XF_PROJECT_PATH / "xfusion/components")
            fc.update_component_md5(key, group_name)
            logging.info(f"{key} 部分导出完成")

        # ports
        DIR_PORTS_XFUSION = api.XF_ROOT / "ports/pt/pt3210"
        dict_ports = user_collect(DIR_PORTS_XFUSION)
        key = "ports"
        copy_path_base = api.XF_PROJECT_PATH / "xfusion"
        self.update_component(uvprojx, key, dict_ports, copy_path_base)
        fc.update_custom_md5(key, DIR_PORTS_XFUSION.as_posix())
        logging.info(f"{key} 部分导出完成")

        uvprojx.save(self.PATH_UVPROJX)
        fc.save(self.DIR_PROJECT / "FileChange.json")

        logging.info(f"{self.PROJECT_NAME} 工程导出完毕!")

    @hookimpl
    def update(self, name, args):
        name = Path(name)

        self.PROJECT_NAME = os.path.basename(name)
        self.DIR_PROJECT = api.XF_PROJECT_PATH / self.PROJECT_NAME
        self.PATH_UVPROJX = self.DIR_PROJECT / f"{self.PROJECT_NAME}.uvprojx"
        self.PATH_BUILD_ENV = "build/build_environ.json"
        self.FILE_MD5 = self.DIR_PROJECT / "FileChange.json"

        # 检查 update 所需文件
        if not self.FILE_MD5.exists():
            logging.error(f"{self.PROJECT_NAME} 工程的 FileChange.json 文件不存在, xf update 终止！")
            return

        uvprojx = MDK(self.PATH_UVPROJX)
        fc = FileChange(self.PATH_BUILD_ENV, self.FILE_MD5)
        with open(self.PATH_BUILD_ENV, "r") as f:
            build_env = json.load(f)

        # NOTE: platform 不会常修改，目前不做 update
        # platform
        DIR_PLATFORM_WORKSPACE = api.XF_PROJECT_PATH / "platform"
        if not DIR_PLATFORM_WORKSPACE.exists():
            shutil.copytree(api.XF_TARGET_PATH / "platform", 
                            DIR_PLATFORM_WORKSPACE, 
                            dirs_exist_ok=True)

        key = "platform"
        srcs = [
            "./drvs/src/*.c",
            "./main.c"
        ]
        incs = [
            "./core/",
            "./core/reg/",
            "./drvs/includes/"
        ]
        dict_platform = user_collect(DIR_PLATFORM_WORKSPACE, srcs, incs)
        self.update_component(uvprojx, key, dict_platform)
        logging.info(f"已更新 {key} 模块")

        # freertos
        if api.get_define("PORT_USE_FREERTOS"):
            key = "freertos"
            srcs = [
                "./port/port.c",
                "./src/*.c",
            ]
            incs = [
                "./include/",
                "./port/",
            ]
            dict_freertos = user_collect(DIR_PLATFORM_WORKSPACE / "freertos", srcs, incs)
            self.update_component(uvprojx, key, dict_freertos)
            logging.info(f"已更新 {key} 模块")

        # user_main
        key = "user_main"
        if fc.is_component_changed(key):
            self.update_component(uvprojx, key, build_env[key])
            logging.info(f"已更新 {key} 模块")

        def __update_group(fc:FileChange, uvprojx:MDK, 
                           build_env, group_name, 
                           copy_path_base=None):
            ## 检查新增 / 删除
            added, removed = fc.get_component_diff(group_name)
            if added:
                for key, value in added.items():
                    fc.update_component_md5(key, group_name)
                    self.update_component(uvprojx, key, value, copy_path_base)
                    logging.info(f"已增加 {key} 模块")

            if removed:
                for key, value in removed.items():
                    uvprojx.remove_group(key)
                    # TODO: 头文件未移除
                    logging.info(f"已移除 {key} 模块")

            ## 检查修改
            components = build_env[group_name]
            for key, value in components.items():
                if key in added.keys() or key in removed.keys():
                    continue
                if fc.is_component_changed(key, group_name):
                    self.update_component(uvprojx, key, value, copy_path_base)
                    logging.info(f"已更新 {key} 模块")

        # user_components
        __update_group(fc, uvprojx, build_env, "user_components")

        # user_dir
        __update_group(fc, uvprojx, build_env, "user_dirs")

        # public_components
        __update_group(fc, uvprojx, build_env, "public_components",
                       api.XF_PROJECT_PATH / "xfusion/components")

        # ports
        DIR_PORTS_XFUSION = api.XF_ROOT / "ports/pt/pt3210"
        key = "ports"
        dict_ports = user_collect(DIR_PORTS_XFUSION)
        if fc.is_custom_changed(key, DIR_PORTS_XFUSION.as_posix()):
            copy_path_base = api.XF_PROJECT_PATH / "xfusion"
            self.update_component(uvprojx, key, dict_ports, copy_path_base)
            logging.info(f"已更新 {key} 模块")

        uvprojx.save(self.PATH_UVPROJX)
        fc.save(self.DIR_PROJECT / "FileChange.json")

        logging.info(f"{self.PROJECT_NAME} 工程更新完毕!")

    @hookimpl
    def menuconfig(self, args):
        logging.error("pt3210 当前不支持 xf menuconfig 命令!")
