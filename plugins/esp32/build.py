import xf_build
from xf_build import api
import logging
from pathlib import Path
import os
import shutil


class esp32():

    def build(self, args):
        api.apply_components_template("components.j2", "CMakeLists.txt")
        api.apply_template("project.j2", api.XF_TARGET_PATH / "CMakeLists.txt")
        api.cd_to_target()
        idf_components: Path = api.XF_TARGET_PATH / "components"
        public_components: Path = api.PROJECT_BUILD_PATH / "public_components"
        user_components: Path = api.PROJECT_BUILD_PATH / "user_components"
        user_dirs: Path = api.PROJECT_BUILD_PATH / "user_dirs"
        user_main: Path = api.PROJECT_BUILD_PATH / "user_main"
        if idf_components.exists():
            shutil.rmtree(idf_components)
        idf_components.mkdir()
        # 复制public_components里面的文件夹到components下面
        for item in public_components.iterdir():
            target_path = idf_components / item.name
            shutil.copytree(item, target_path)
        # 复制user_components里面的文件夹到components下面
        if user_components.exists():
            for item in user_components.iterdir():
                target_path = idf_components / item.name
                shutil.copytree(item, target_path)
        if user_dirs.exists():
            for item in user_dirs.iterdir():
                target_path = idf_components / item.name
                shutil.copytree(item, target_path)
        # 复制user_main里面的文件夹到components下面
        shutil.copytree(user_main, idf_components / "user_main")
        # 执行底层指令
        cmd = ["idf.py", "build", *args]
        os.system(" ".join(cmd))

    def clean(self, args):
        api.cd_to_target()
        idf_components = api.XF_TARGET_PATH / "components"
        if idf_components.exists():
            shutil.rmtree(idf_components)
        cmd = ["idf.py", "fullclean", *args]
        os.system(" ".join(cmd))

    def flash(self, args):
        api.cd_to_target()
        cmd = ["idf.py", "flash", *args]
        os.system(" ".join(cmd))

    def export(self, name, args):
        print("export")

    def update(self, name, args):
        print("update")

    def menuconfig(self, args):
        if args[0] == "sub":
            api.cd_to_target()
            os.system("idf.py menuconfig")
