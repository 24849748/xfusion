from lxml import etree
import os
from pathlib import Path

class MDK:
    def __init__(self, name) -> None:
        self.DIR_PROJECT = os.path.dirname(os.path.abspath(name))

        self.tree = etree.parse(name)
        self.IncludePath = self.tree.xpath("//Cads/VariousControls/IncludePath")[0]
        if self.IncludePath.text:
            self.ctxIncludePath = set(self.IncludePath.text.split(";"))
        else:
            self.ctxIncludePath = set()

        self.MiscControls = self.tree.xpath("//Cads/VariousControls/MiscControls")[0]
        self.ctxMiscControls = set()

        self.Groups = self.tree.xpath("//Groups")[0]

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

    def save(self, name):
        # MiscControls
        self.ctxMiscControls = sorted(list(self.ctxMiscControls))
        self.MiscControls.text += " " + " ".join(self.ctxMiscControls)
        # IncludePath
        self.ctxIncludePath = sorted(list(self.ctxIncludePath))
        self.IncludePath.text = ";".join(self.ctxIncludePath)
        
        # 关闭标签自闭合
        Targets = self.tree.xpath("//Targets")[0]
        for node in Targets.iter():
            if node.text is None:
                node.text = ""
        
        # 保持缩进
        etree.indent(self.tree, space="  ")

        # 保持 Project 下标签空行
        Project = self.tree.xpath("//Project")[0]
        for i, child in enumerate(Project):
            child.tail = "\n\n  "
        Project.text = "\n\n  "
        Project[-1].tail = "\n\n"

        with open(name, "wb") as file:
            file.write(b'<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
            self.tree.write(file, encoding="utf-8", pretty_print=True)

    def set_target(self, name):
        element = self.tree.xpath("//TargetName")[0]
        element.text = name

        element = self.tree.xpath("//OutputName")[0]
        element.text = name

    def set_device(self, name):
        element = self.tree.xpath("//Device")[0]
        element.text = name

    def set_startup(self, name):
        element = self.tree.xpath("//Group[1]/Files/File/FileName")[0]
        element.text = name
        element = self.tree.xpath("//Group[1]/Files/File/FilePath")[0]
        element.text = name

    def set_cpu(
        self,
        IRAM_end,
        IROM_end,
        IRAM_start="0x20000000",
        IROM_start="0x8000000",
        CLOCK="8000000",
        CPUTYPE="Cortex-M3",
        other="TZ",
    ):
        text = f'IRAM({IRAM_start}-{IRAM_end}) IROM({IROM_start}-{IROM_end}) CLOCK({CLOCK}) CPUTYPE("{CPUTYPE}") {other}'
        element = self.tree.xpath("//Cpu")[0]
        element.text = text

    def set_define(
        self,
        define,
        base="USE_FULL_LL_DRIVER,HSE_VALUE=8000000,HSE_STARTUP_TIMEOUT=100,LSE_STARTUP_TIMEOUT=5000,LSE_VALUE=32768,HSI_VALUE=8000000,LSI_VALUE=40000,VDD_VALUE=3300,PREFETCH_ENABLE=1",
    ):
        element = self.tree.xpath("//Cads/VariousControls/Define")[0]
        element.text = base + ", " + define

    def set_c99(self, enable):
        result = self.tree.xpath(f"//uC99")[0]
        if enable:
            result.text = "1"
        else:
            result.text = "0"

    def set_gnu(self, enable):
        result = self.tree.xpath(f"//uGnu")[0]
        if enable:
            result.text = "1"
        else:
            result.text = "0"

    def add_group(self, group):
        elements = self.tree.xpath("//GroupName")
        if group in [i.text for i in elements]:
            return

        element = etree.Element("Group")
        group_name = etree.SubElement(element, "GroupName")
        group_name.text = group
        etree.SubElement(element, "Files")

        self.Groups.append(element)

        return element

    def remove_group(self, group):
        result = self.Groups.xpath(f".//Group[GroupName='{group}']")
        if len(result) > 0:
            Group = result[0]
            self.Groups.remove(Group)

    def __add_file(self, file):
        element = etree.Element("File")
        file_name = etree.SubElement(element, "FileName")
        file_type = etree.SubElement(element, "FileType")
        file_path = etree.SubElement(element, "FilePath")
        file_name.text = os.path.basename(file)
        file_path.text = file
        _, file_extension = os.path.splitext(file_name.text)
        if file_extension == ".c":
            file_type.text = "1"
        elif file_extension == ".s" or file_extension == ".S":
            file_type.text = "2"
        elif file_extension == ".o":
            file_type.text = "3"
        elif file_extension == ".lib":
            file_type.text = "4"
        elif file_extension == ".h":
            file_type.text = "5"
        elif file_extension == ".cpp" or file_extension == ".cxx":
            file_type.text = "8"
        else:
            file_type.text = "9"
        return element

    def update_files(self, group, files):
        """
        将 group 中原来的文件列表更新为 files 
        """
        if not files:
            return

        files = self.to_project_relpaths(files)

        result = self.Groups.xpath(f".//Group[GroupName='{group}']")
        if len(result) == 0:
            elemGroup = self.add_group(group)
        else:
            elemGroup = result[0]

        elemFiles = elemGroup.xpath(f".//Files")[0]
        elemFilePaths = elemGroup.xpath(f".//FilePath")
        lastfiles = set([i.text for i in elemFilePaths])

        if isinstance(files, str):
            currfiles = set([files])
        elif isinstance(files, list):
            currfiles = set(files)

        added = currfiles - lastfiles
        removed = lastfiles - currfiles

        for i in added:
            elemFiles.append(self.__add_file(i))
        for i in removed:
            elem = elemFiles.xpath(f".//FilePath[text()='{i}']")[0].getparent()
            elemFiles.remove(elem)

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
        ScatterFile = self.tree.xpath("//LDads/ScatterFile")[0]
        ScatterFile.text = path

class UVPROJX_325x(MDK):
    def __init__(self, path_project):
        super().__init__(path_project)

    def set_blelib(self, path_lib):
        group_name = "ble"
        result = self.Groups.xpath(f".//Group[GroupName='{group_name}']")

        if len(result) == 0:
            self.update_files(group_name, path_lib)
        else:
            path_lib = self.to_project_relpaths(path_lib)
            elemGroup = result[0]
            elemFileName = elemGroup.xpath(f".//Files/File/FileName")[0]
            elemFileName.text = os.path.basename(path_lib)
            elemFilePath = elemGroup.xpath(f".//Files/File/FilePath")[0]
            elemFilePath.text = path_lib
