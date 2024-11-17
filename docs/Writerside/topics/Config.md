# Config

Firework Config 修改自 [Kayaku](https://github.com/GraiaProject/kayaku)。

## 基本使用

声明一个 `dataclass` 类型的配置类，然后通过 `ConfigManager` 加载配置。

```py
from firework.config import ConfigManager

from dataclasses import dataclass

@dataclass
class Config:
    token: str

cm = ConfigManager({"{**}": "./.firework/config/{**}"})
cm.load("config", Config)
conf = cm.get(Config)
print(conf.token)
```

配合 Bootstrap 和 `firework run` 使用时，通过 `ConfigManager.current` 方法获取实例。

```py
async def launch(self, ctx: ServiceContext):
    async with ctx.prepare():
        cm = ConfigManager.current()
        cm.load("config", Config)
        conf = cm.get(Config)
        print(conf.token)
    
    ...
```

需要注意的，如果配置读取失败，目前的实现行为上不是我们所希望的，这点会在未来版本中进行改进。
