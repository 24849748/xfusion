import xf_build
from xf_build import api
import shutil
import json
from .mdk import MDK
import os
import hashlib
from pathlib import Path
import logging

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

def get_build_info(path_build_env):
    """
    1. 过滤 srcs 为空的 components
    2. 给列表排序防止 FileChange.json 无意义的修改
    """
    with open(path_build_env, "r") as f:
        build_env = json.load(f)

    def __get_empty_components(data, parent_key=None):
        """
        收集未开启的组件，判断条件：srcs 列表为空
        """
        empty_components = []
        if isinstance(data, dict):
            if 'srcs' in data and isinstance(data['srcs'], list) and len(data['srcs']) == 0:
                empty_components.append(parent_key)
            for key, value in data.items():
                empty_components.extend(__get_empty_components(value, key))
        elif isinstance(data, list):
        # 递归检查列表中的每个元素
            for item in data:
                empty_components.extend(__get_empty_components(item, parent_key))
        return empty_components

    key_to_remove = __get_empty_components(build_env)

    # 移除未开启的组件、requires、cflags
    key_to_remove.extend(["requires", "cflags"])

    def __simpify(data, keys_to_remove):
        if isinstance(data, dict):
            # 创建一个新的字典，排除掉键在 keys_to_remove 中的键值对
            return {k: __simpify(v, keys_to_remove) for k, v in data.items() if k not in keys_to_remove}
        elif isinstance(data, list):
            # 如果是列表，递归处理每个元素
            return sorted([__simpify(item, keys_to_remove) for item in data])
        else:
            # 如果是其他数据类型，直接返回
            return data

    return __simpify(build_env, key_to_remove)

def calc_folder_md5(path):
    def calc_file_md5(file_path):
        """计算单个文件的MD5值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    md5_hash = hashlib.md5()
    # 遍历文件夹
    for root, _, files in os.walk(path):
        for file in sorted(files):  # 排序以保证顺序一致
            file_path = os.path.join(root, file)

            # 更新文件的MD5到文件夹的总MD5
            file_md5 = calc_file_md5(file_path)
            md5_hash.update(file_md5.encode())

    return md5_hash.hexdigest()

def boards_copy_ignore(src, names):
    exclude = {
        "output",
        "JlinkLog.txt",
        "target.json",
        "xfconfig.defaults",
        "XFKconfig"
    }
    return {name for name in names if name in exclude}

def sdk_copy_ignore(src, names):
    # 屏蔽底层SDK中不需要的文件或目录
    exclude_map = {
        "": {"docs", ".git", ".gitignore", "examples", "modules", "README.md"}, # 根目录
        "core": {"pt3210.h", "mdk"}, # core 目录
    }
    exclude = exclude_map.get(Path(src).name, exclude_map[""])

    return {name for name in names if name in exclude}

def ports_copy_ignore(src, names):
    exclude = {
        "xf_collect.py",
        "XFKconfig"
    }
    return {name for name in names if name in exclude}


class pt3210():
    def update_component(self, mdk:MDK, key, value, copy_path_base=None, copy_ignore=None):
        """
        增量更新基础组件
        """
        temp = {
            "srcs": value["srcs"],
            "inc_dirs": value["inc_dirs"],
        }

        # 需要拷贝到本地的
        if copy_path_base is not None:
            _path = Path(copy_path_base) / key
            if _path.exists():
                shutil.rmtree(_path)
            shutil.copytree(value["path"], _path, dirs_exist_ok=True, ignore=copy_ignore)
            temp["srcs"] = change_path_base(value["path"], _path, value["srcs"])
            temp["inc_dirs"] = change_path_base(value["path"], _path, value["inc_dirs"])

        mdk.update_files(key, value["srcs"])
        mdk.add_include_path(value["inc_dirs"])

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

    def build(self, args):
        logging.error("pt3210 当前不支持 xf build 命令!")

    def clean(self, args):
        logging.error("pt3210 当前不支持 xf clean 命令!")

    def flash(self, args):
        logging.error("pt3210 当前不支持 xf flash 命令!")

    def export(self, name, args):
        if not (api.XF_ROOT / "sdks/pt3210_sdk").exists():
            logging.error("请先执行 'xf target -d' 下载原始 sdk 源码")
            return
        if name is None:
            return
        name = Path(name)

        self.PROJECT_NAME = os.path.basename(name)
        self.DIR_PROJECT = api.XF_PROJECT_PATH / self.PROJECT_NAME
        self.PATH_UVOPTX = self.DIR_PROJECT / f"{self.PROJECT_NAME}.uvoptx"
        self.PATH_UVPROJX = self.DIR_PROJECT / f"{self.PROJECT_NAME}.uvprojx"
        self.PATH_BUILD_ENV = api.XF_PROJECT_PATH / "build/build_environ.json"
        self.PATH_PROJ_INFO = self.DIR_PROJECT / "project_info.json"

        # build_environ 预处理：
        build_env = get_build_info(self.PATH_BUILD_ENV)
        build_env["public_port"]["ports"] = build_env["public_port"].pop("pt3210")

        # 拷贝 boards
        shutil.copytree(api.XF_TARGET_PATH,
                        self.DIR_PROJECT,
                        dirs_exist_ok=True,
                        ignore=boards_copy_ignore)

        mdk = MDK(self.PATH_UVPROJX, api.XF_ROOT / "plugins/pt3210")
        mdk.set_target(self.PROJECT_NAME)
        mdk.set_preinclude(api.XF_PROJECT_PATH / "build/header_config/xfconfig.h")
        mdk.set_device("PT3210-Hxxx", "PTW", "PTW.PT3210.1.0.0")
        mdk.set_sw_param("0x20000000", "0x3000", ".\\Flash\\PT3210_256KB_FLASH_PH.FLM", 
                        "0x18000000", "0x40000")
        mdk.set_ScatterFile(self.DIR_PROJECT / "link.sct")

        ## 拷贝平台 sdk
        DIR_PLAT_WORKSPACE = api.XF_PROJECT_PATH / "platform"
        shutil.copytree(api.XF_ROOT / "sdks/pt3210_sdk", 
                        DIR_PLAT_WORKSPACE, 
                        dirs_exist_ok=True,
                        ignore=sdk_copy_ignore)
        mdk.add_include_path([
            DIR_PLAT_WORKSPACE / "core/reg",
            DIR_PLAT_WORKSPACE / "core",
            DIR_PLAT_WORKSPACE / "drivers/api",
        ])
        mdk.update_files("core", [
            self.DIR_PROJECT / "startup.s",
            self.DIR_PROJECT / "main.c",
        ])
        mdk.update_files("drivers", [
            DIR_PLAT_WORKSPACE / "drivers/api/drvs.h",
            DIR_PLAT_WORKSPACE / "drivers/lib/drvs.lib"
        ])

        ## export 逻辑是 sdk -> 工程 单向更新，移植阶段可屏蔽
        # port
        self.update_component(mdk, "ports", build_env["public_port"]["ports"],
                              copy_path_base = api.XF_PROJECT_PATH / "xfusion",
                              copy_ignore=ports_copy_ignore)
        md5 = calc_folder_md5(build_env["public_port"]["ports"]["path"])
        build_env["public_port"]["ports"]["md5"] = md5
        logging.info(f"ports 导出完成")

        # user_main
        self.update_component(mdk, "user_main", build_env["user_main"])
        md5 = calc_folder_md5(build_env["user_main"]["path"])
        build_env["user_main"]["md5"] = md5
        logging.info(f"user_main 导出完成")

        # user_components
        group_name = "user_components"
        for key, value in build_env[group_name].items():
            self.update_component(mdk, key, value)
            md5 = calc_folder_md5(build_env[group_name][key]["path"])
            build_env[group_name][key]["md5"] = md5
            logging.info(f"{group_name} {key} 导出完成")

        # user_dirs
        group_name = "user_dirs"
        for key, value in build_env[group_name].items():
            self.update_component(mdk, key, value)
            md5 = calc_folder_md5(build_env[group_name][key]["path"])
            build_env[group_name][key]["md5"] = md5
            logging.info(f"{group_name} {key} 导出完成")

        # public_components
        group_name = "public_components"
        for key, value in build_env[group_name].items():
            self.update_component(mdk, key, value,
                                  copy_path_base = api.XF_PROJECT_PATH / "xfusion/components")
            md5 = calc_folder_md5(build_env[group_name][key]["path"])
            build_env[group_name][key]["md5"] = md5
            logging.info(f"{group_name} {key} 导出完成")

        mdk.save_uvoptx(self.PATH_UVOPTX)
        mdk.save_uvprojx(self.PATH_UVPROJX)
        mdk.save_info(self.PATH_PROJ_INFO)
        with open(self.DIR_PROJECT / "FileChange.json", "w") as f:
            json.dump(build_env, f, indent=4)

        logging.info(f"{self.PROJECT_NAME} 工程导出完毕!")

    def update(self, name, args):
        name = Path(name)

        self.PROJECT_NAME = os.path.basename(name)
        self.DIR_PROJECT = api.XF_PROJECT_PATH / self.PROJECT_NAME
        self.PATH_UVOPTX = self.DIR_PROJECT / f"{self.PROJECT_NAME}.uvoptx"
        self.PATH_UVPROJX = self.DIR_PROJECT / f"{self.PROJECT_NAME}.uvprojx"
        self.PATH_BUILD_ENV = "build/build_environ.json"
        self.FILE_MD5 = self.DIR_PROJECT / "FileChange.json"
        self.PATH_PROJ_INFO = self.DIR_PROJECT / "project_info.json"

        # 检查 update 所需文件
        if not self.FILE_MD5.exists():
            logging.error(f"缺少 {self.FILE_MD5.as_posix()} 文件, xf update 终止!")
            return
        if not self.PATH_PROJ_INFO.exists():
            logging.error(f"缺少 {self.FILE_MD5.as_posix()} 文件, xf update 终止!")
            return

        with open(self.FILE_MD5, "r") as f:
            fileChange = json.load(f)
        with open(self.PATH_PROJ_INFO, "r") as f:
            proj_info = json.load(f)

        mdk = MDK(self.PATH_UVPROJX, api.XF_ROOT / "plugins/pt3210", proj_info)
        build_env = get_build_info(self.PATH_BUILD_ENV)
        build_env["public_port"]["ports"] = build_env["public_port"].pop("pt3210")

        # 平台 sdk 相关
        DIR_PLAT_WORKSPACE = api.XF_PROJECT_PATH / "platform"
        if not DIR_PLAT_WORKSPACE.exists():
            shutil.copytree(api.XF_ROOT / "sdks/pt3210_sdk",
                            DIR_PLAT_WORKSPACE,
                            dirs_exist_ok=True,
                            ignore=sdk_copy_ignore)

        # ports
        key = "ports"
        md5 = calc_folder_md5(build_env["public_port"]["ports"]["path"])
        build_env["public_port"]["ports"]["md5"] = md5
        if md5 != fileChange["public_port"]["ports"]["md5"]:
            self.update_component(mdk, key, build_env["public_port"][key],
                                  api.XF_PROJECT_PATH / "xfusion",
                                  copy_ignore=ports_copy_ignore)
            logging.info(f">>> {key} 模块已更新")
        else:
            logging.info(f"=== {key} 模块无需更新")
        # user_main
        key = "user_main"
        md5 = calc_folder_md5(build_env["user_main"]["path"])
        build_env["user_main"]["md5"] = md5
        if md5 != fileChange["user_main"]["md5"]:
            self.update_component(mdk, key, build_env[key])
            logging.info(f">>> {key} 模块已更新")
        else:
            logging.info(f"=== {key} 模块无需更新")

        def get_component_diff(curr, last):
            added = {k: v for k, v in curr.items() if k not in last}
            removed = {k: v for k, v in last.items() if k not in curr}
            return added, removed

        def __update_group(mdk:MDK, fileChange,
                           build_env, group_name,
                           copy_path_base=None):
            ## 检查新增 / 删除
            added, removed = get_component_diff(build_env[group_name],
                                                fileChange[group_name])
            if added:
                for key, value in added.items():
                    md5 = calc_folder_md5(build_env[group_name][key]["path"])
                    build_env[group_name][key]["md5"] = md5
                    self.update_component(mdk, key, value, copy_path_base)
                    logging.info(f"+++ {key} 模块已增加")

            if removed:
                for key, value in removed.items():
                    if copy_path_base is not None:
                        _path = Path(copy_path_base) / key
                        to_remove_incs = change_path_base(value["path"], _path, value["inc_dirs"])
                    else:
                        to_remove_incs = value["inc_dirs"]
                    mdk.remove_include_path(to_remove_incs)
                    mdk.remove_group(key)
                    logging.info(f"--- {key} 模块已移除")

            ## 检查修改
            components = build_env[group_name]
            for key, value in components.items():
                if key in added.keys() or key in removed.keys():
                    continue

                md5 = calc_folder_md5(build_env[group_name][key]["path"])
                build_env[group_name][key]["md5"] = md5
                if md5 != fileChange[group_name][key]["md5"]:
                    self.update_component(mdk, key, value, copy_path_base)
                    logging.info(f">>> {key} 模块已更新")
                else:
                    logging.info(f"=== {key} 模块无需更新")

        # user_components
        __update_group(mdk, fileChange, build_env, "user_components")

        # user_dir
        __update_group(mdk, fileChange, build_env, "user_dirs")

        # public_components
        __update_group(mdk, fileChange, build_env, "public_components",
                       api.XF_PROJECT_PATH / "xfusion/components")

        mdk.save_uvprojx(self.PATH_UVPROJX)
        mdk.save_uvoptx(self.PATH_UVOPTX)
        mdk.save_info(self.PATH_PROJ_INFO)

        with open(self.FILE_MD5, "w") as f:
            json.dump(build_env, f, indent=4)

        logging.info(f"{self.PROJECT_NAME} 工程更新完毕!")

    def menuconfig(self, args):
        logging.error("pt3210 当前不支持 xf menuconfig 命令!")
