import re
from pathlib import Path

from git import Repo


class MapRepo:
    def __init__(self):
        self.classes = []
        self.methods = []
        self.fields = []

    def addClass(self, classMap):
        self.classes.append(classMap)

    def addField(self, fieldMap):
        self.fields.append(fieldMap)

    def addMethod(self, methodMap):
        self.methods.append(methodMap)

    def getMethodByObf(self, obfMethod):
        for method in self.methods:
            if method.obfName == obfMethod:
                yield method

    def getFieldByObf(self, obfField):
        for field in self.fields:
            if field.obfName == obfField:
                yield field

    def getClassByObf(self, obfClass):
        for clazz in self.classes:
            if clazz.obfName == obfClass:
                yield clazz

    def dump(self):
        return '\n'.join([
            str(x) for x in (self.classes + self.methods + self.fields)
        ])


class ClassMap:
    def __init__(self, obfPath, obfName, realPath, realName):
        self.obfPath = obfPath
        self.obfName = obfName
        self.realPath = realPath
        self.realName = realName

    def __str__(self):
        return (
            f"{self.obfPath}{self.obfName} -> {self.realPath}{self.realName}"
        )


class ClassFactory:
    def __init__(self, mapRepo):
        self.mapRepo = mapRepo
        self.classMatcher = r'CLASS (.*\/)(class_\w+) (.*\/)(\w.*)'
        self.subClass = r'\s+CLASS (class_\w+) (\w.*)'
        self.nonObfMatcher = r'CLASS (.*\/)(\w.*)'

    def getObfClass(self, obfName):
        return self.mapRepo.getClassByObf(obfName)

    def getClasses(self, path):
        toplevel = None
        txt = path.read_text()
        for match in re.finditer(self.classMatcher, txt):
            self.mapRepo.addClass(
                ClassMap(match[1], match[2], match[3], match[4])
            )
            if toplevel is None:
                toplevel = ClassMap(match[1], match[2], match[3], match[4])
        if toplevel is None:
            for match in re.finditer(self.nonObfMatcher, txt):
                self.mapRepo.addClass(
                    ClassMap(match[1], match[2], match[1], match[2])
                )
                if toplevel is None:
                    toplevel = ClassMap(match[1], match[2], match[1], match[2])
        for match in re.finditer(self.subClass, txt):
            self.mapRepo.addClass(
                ClassMap(
                    toplevel.obfPath,
                    f"{toplevel.obfName}.{match[1]}",
                    toplevel.realPath,
                    f"{toplevel.realName}.{match[2]}"
                )
            )
        return toplevel


class FieldMap:
    def __init__(self, obfPath, obfName, realPath, realName):
        self.obfPath = obfPath
        self.obfName = obfName
        self.realPath = realPath
        self.realName = realName

    def __str__(self):
        return (
            f"{self.obfPath}.{self.obfName} -> {self.realPath}.{self.realName}"
        )


class FieldFactory:
    def __init__(self, mapRepo):
        self.mapRepo = mapRepo
        self.fieldMatcher = r'FIELD (field_\w+) (\w.*) '

    def getObfField(self, obfName):
        return self.mapRepo.getFieldByObf(obfName)

    def getFields(self, path, toplevel):
        txt = path.read_text()
        for match in re.finditer(self.fieldMatcher, txt):
            self.mapRepo.addField(
                FieldMap(
                    f"{toplevel.obfPath}{toplevel.obfName}",
                    match[1],
                    f"{toplevel.realPath}{toplevel.realName}",
                    match[2]
                )
            )


class MethodMap:
    def __init__(self, obfPath, obfName, realPath, realName):
        self.obfPath = obfPath
        self.obfName = obfName
        self.realPath = realPath
        self.realName = realName

    def __str__(self):
        return (
            f"{self.obfPath}.{self.obfName} -> {self.realPath}.{self.realName}"
        )


class MethodFactory:
    def __init__(self, mapRepo):
        self.mapRepo = mapRepo
        self.methodMatcher = r'METHOD (method_\w+) (\w.*) '

    def getObfMethod(self, obfName):
        return self.mapRepo.getMethodByObf(obfName)

    def getMethods(self, path, toplevel):
        txt = path.read_text()
        for match in re.finditer(self.methodMatcher, txt):
            self.mapRepo.addMethod(
                MethodMap(
                    f"{toplevel.obfPath}{toplevel.obfName}",
                    match[1],
                    f"{toplevel.realPath}{toplevel.realName}",
                    match[2]
                )
            )


if __name__ == "__main__":
    yarnDir = Path("./yarn")
    if not yarnDir.exists():
        Repo.clone_from("git@github.com:FabricMC/yarn.git", yarnDir)
    mappingDir = Path("./yarn/mappings")
    mapRepo = MapRepo()
    classes = ClassFactory(mapRepo)
    for file in mappingDir.glob('**/*.mapping'):
        print("Parsing file: ", file)
        topLvl = classes.getClasses(
            file
        )
        fields = FieldFactory(mapRepo)
        fields.getFields(
            file,
            topLvl
        )
        methods = MethodFactory(mapRepo)
        methods.getMethods(
            file,
            topLvl
        )
    Path('./out.txt').write_text(mapRepo.dump())
