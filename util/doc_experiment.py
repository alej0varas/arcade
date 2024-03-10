"""
An attempt generating docs in a cleaner way.

The ideas is to:
* Make a tool generating docs for a module using autodoc or define explicit members.
* Integration test: Perform deep inspection of the entire arcade package ensuring things are documented.

Separate getters and setters looking at decorators.

    decorator_list=[
        Name(id='property', ctx=Load())],

    decorator_list=[
        Attribute(
            value=Name(id='viewport', ctx=Load()),
            attr='setter',
            ctx=Load())],
"""
import ast
from pathlib import Path
from typing import Dict

EXCLUDE_MODULES = set([
    "examples",
    "experimental",
])

# Describe the rst doc structure.
# The TOC is generated in the oder of the list.
# We can write all members or a subset of them to a document.
# TODO: Go by python file or rst document?
DOC_STRUCT = [
    (
        "sprites.rst", {
            "modules": [
                {
                    "path": "arcade/__init__.py",
                    "members": "__all__",
                }
            ]
        }
    ),
    (
        "spritelist.rst", {
            "modules": [
                {
                    "path": "arcade/__init__.py",
                    "members": "__all__",
                }
            ],
        },
    ),
    (
        "textures.rst", {
            "modules": [
                {
                    "path": "arcade/__init__.py",
                    "members": "__all__",
                }
            ]
        }
    )
]


 # NOTE: Later we can inspect class members to generate more detailed docs
class ClassInfo:
    def __init__(self, name: str):
        self.name = name
        # Collected data
        self.methods = []
        self.properties = []  # variables or methods with @property


class ModuleInfo:
    """General info about module members"""
    def __init__(self, path: Path):
        self._file_path = path
        self._source = None
        if self._file_path.is_file():
            self._source = self._file_path.read_text()
            self._tree = ast.parse(self._source)

        # Collected data
        self.classes = []
        self.functions = []
        self.variables = []
        self.imports = []
        # Child modules
        self.children: Dict[str, ModuleInfo] = {}

        # if self._file_path.is_file():
        #     self._parse_module()

    @property
    def module_path(self) -> str:
        parts = (*self._file_path.parts[:-1], self.module_name)
        return ".".join(parts)

    @property
    def module_name(self) -> str:
        return self._file_path.stem.strip()

    def _parse_module(self):
        """Extract the relevant module info"""
        for node in self._tree.body:
            # Classes
            if isinstance(node, ast.ClassDef):
                self._parse_class(node)

            # Functions
            if isinstance(node, ast.FunctionDef):
                self._parse_module_function(node)

            # Variables
            if isinstance(node, ast.Assign):
                self._parse_module_variable(node)

            # Imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    print("Import", alias.name)

    def _parse_class(self, node: ast.ClassDef):
        """Extract the relevant class info"""
        pass

    def _parse_module_function(self, node: ast.FunctionDef):
        """Extract the relevant function info"""
        pass

    def _parse_module_variable(self, node: ast.Assign):
        """Extract the relevant variable info"""
        pass

    def dump(self) -> str:
        """Dump the module info to a string"""
        return ast.dump(self._tree, indent=4)

    def print_tree(self, level: int = 0):
        """Print the module tree"""
        for module in self.children.values():
            print(f"{' ' * (level * 2)}{module.module_name}")
            module.print_tree(level + 1)


# for node in tree.body:  # ast.walk(tree):
#     # Classes
#     if isinstance(node, ast.ClassDef):
#         print(f"class {node.name}")
#         # print(node.lineno)
#         # print(node.col_offset)
#         # print(node.body)

#     # Functions
#     if isinstance(node, ast.FunctionDef):
#         print(f"def {node.name} {node.decorator_list}")

#     # Variables
#     if isinstance(node, ast.Assign):
#         print(f"var: {node.targets[0].id}")
#         # for name in node.targets:
#         #     print(f" -> {name.id}")


# path = Path("arcade/gl/context.py")
# path = Path("arcade/__init__.py")
# path = Path("arcade/types.py")
# path = Path("arcade/texture_atlas/atlas_2d.py")
# path = Path("arcade/application.py")
# mod = ModuleInfo(path)
# print(mod.dump())


def build_module_tree() -> ModuleInfo:
    root_path = Path("arcade")
    root_module = ModuleInfo(path=Path("arcade"))
    recurse_dir(root_path, root_module)
    return root_module


def recurse_dir(dir: Path, parent: ModuleInfo):
    for path in dir.iterdir():
        if path.is_dir() and path.stem not in EXCLUDE_MODULES:
            module = ModuleInfo(path=path)
            modules = recurse_dir(path, module)
            if len(modules) > 0:
                parent.children[module.module_name] = module
        elif path.is_file() and path.suffix == ".py":
            module = ModuleInfo(path=path)
            # print(module.module_path, " | ",module.module_name)
            parent.children[module.module_name] = module

    return parent.children.values()


root = build_module_tree()
print("arcade")
root.print_tree(level=1)
