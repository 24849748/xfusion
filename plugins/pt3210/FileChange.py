import json
import hashlib
import os

class FileChange():
    def __init__(self, path_build_env, last = None):
        """
        Parameters:
            path_build_env: "build/build_environ.json"
            last: "project/FileChange.json", export 时不需要指定
        """
        with open (path_build_env, "r") as f:
            self.change = json.load(f)

        # keys_to_remove = ["srcs", "inc_dirs", "cflags", "requires"]
        # self.change = self.__simpify(self.change, keys_to_remove)

        self.last = None
        if last is not None:
            with open (last, "r") as f:
                self.last = json.load(f)

    def __simpify(self, data, keys_to_remove):
        """
        递归移除字典中所有指定的键
        """
        if isinstance(data, dict):
            # 创建一个新的字典，排除掉键在 keys_to_remove 中的键值对
            return {k: self.__simpify(v, keys_to_remove) for k, v in data.items() if k not in keys_to_remove}
        elif isinstance(data, list):
            # 如果是列表，递归处理每个元素
            return [self.__simpify(item, keys_to_remove) for item in data]
        else:
            # 如果是其他数据类型，直接返回
            return data

    def calculate_md5(self, file_path):
        """计算单个文件的MD5值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def calculate_folder_md5(self, folder_path):
        """计算文件夹的MD5值"""
        md5_hash = hashlib.md5()
        # 遍历文件夹
        for root, _, files in os.walk(folder_path):
            for file in sorted(files):  # 排序以保证顺序一致
                file_path = os.path.join(root, file)

                # 更新文件的MD5到文件夹的总MD5
                file_md5 = self.calculate_md5(file_path)
                md5_hash.update(file_md5.encode())

        return md5_hash.hexdigest()

    def update_custom_md5(self, name:str, path:str):
        """ build_env 里未跟踪的文件夹 """
        md5 = self.calculate_folder_md5(path)
        self.change.update({name:{"path":path, "md5":md5}})
        return md5

    def update_component_md5(self, name:str, root:str = None):
        """未指定 root 表示 components 在根路径下"""
        if root is None:
            component = self.change[name]
        else:
            component = self.change[root][name]

        md5 = self.calculate_folder_md5(component["path"])
        component.update({"md5": md5})

        return md5

    def is_custom_changed(self, name:str, path:str):
        """
        判断 build_env 里未跟踪的文件夹是否发生变化，并记录 md5 值
        
        Params:
            name (str): "platform" 或 "port"
            path (str): name 在工作区中的对应路径
        """
        if self.last is None:
            raise Exception("FileChange init时未指定 last")

        curr = self.update_custom_md5(name, path)
        last = self.last[name]["md5"]

        if curr == last:
            return False
        else:
            return True

    def is_component_changed(self, name:str, root:str = None):
        """
        判断组件文件夹是否有更改变化，并记录 md5 值

        Params:
            name (str): 组件文件夹名
            root (str): user_components / user_dirs / public_components，不指定表示一级目录
            path (str): 要计算 md5 的文件夹路径
        """
        if self.last is None:
            raise Exception("FileChange init时未指定 last")

        curr = self.update_component_md5(name, root)

        if root is None:
            last = self.last[name]["md5"]
        else:
            last = self.last[root][name]["md5"]

        if curr == last:
            return False
        else:
            return True

    def get_component_diff(self, root:str):
        """
        获取两个字典新增或移除的键值对
        Params:
            root (str): user_components, user_dirs, public_components
        Returns:
            added (dict): 新增的键值对
            removed (dict): 移除的键值对
        """
        if self.last is None:
            raise Exception("FileChange init时未指定 last")
        if root not in ["user_components", "user_dirs", "public_components"]:
            raise ValueError("root 必须是 user_components, user_dirs, public_components 之一")

        curr = self.change[root]
        last = self.last[root]

        added = {k: v for k, v in curr.items() if k not in last}
        removed = {k: v for k, v in last.items() if k not in curr}
        return added, removed

    def update_custom_info(self, info:dict):
        self.change.update(info)

    def get_custom_info(self, name):
        if self.last is None:
            raise Exception("FileChange init时未指定 last")

        return self.last.get(name)

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.change, f, indent=4)
