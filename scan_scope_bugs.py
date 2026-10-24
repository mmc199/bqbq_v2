"""扫描模块内所有「类方法调用但没加 self./类名」的作用域错误。

这类 bug 的特征：方法 body 里出现 Name 调用，而该名字是所在类
（或任意类）的方法名 —— Python 类体不是作用域，运行时必然 NameError。
"""
import ast
import io

FILES = [
    r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect\commands.py",
    r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect\imagelib.py",
    r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect\main.py",
]

problems = []

for path in FILES:
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)

    # 收集所有类的方法名
    all_methods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    all_methods.add(m.name)

    # 收集模块级函数名与导入名（这些是可以直接调用的）
    module_level = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_level.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    module_level.add(t.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                module_level.add(a.asname or a.name.split(".")[0])

    # 遍历每个类方法，找裸名调用
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        for m in cls.body:
            if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(m):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name in all_methods and name not in module_level:
                        problems.append(
                            (path.split("\\")[-1], cls.name, m.name, name, node.lineno)
                        )

print("=" * 78)
print("扫描：类方法内裸名调用其它方法（必然 NameError）")
print("=" * 78)
if problems:
    for f, cls, meth, target, ln in problems:
        print(f"  !! {f}  {cls}.{meth}()  L{ln}  调用了 {target}()  <- 需加 self. 或类名")
else:
    print("  OK 未发现此类问题")

print()
print("=" * 78)
print("附：各文件的方法名清单（供人工核对）")
print("=" * 78)
for path in FILES:
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        ms = [m.name for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
        statics = [
            m.name for m in cls.body
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(
                isinstance(d, ast.Name) and d.id == "staticmethod"
                for d in m.decorator_list
            )
        ]
        print(f"\n{path.split(chr(92))[-1]} :: {cls.name}")
        print(f"  static: {statics}")
