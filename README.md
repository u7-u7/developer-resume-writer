# 🧩 项目经历写作 Skill

`developer-resume-writer` 的核心很简单：给它一个 Git 项目地址或本地项目文件夹，它会理解项目，再帮你写好简历里的「项目经历 / 项目产出」。

它会先回答“这是什么项目”，再把技术方案整理成能放进简历的文案，不再只丢给你一串技术名词。✨

## 能做什么

- 🔎 读取 Git 仓库或本地项目目录，理解项目类型、服务场景和核心能力。
- 🧠 从 README、目录结构和关键源码中梳理技术方案、模块划分和实现亮点。
- 📝 生成项目名称、项目简介、技术栈和 3–5 条项目产出。
- 📄 实际生成 `项目经历.md`；需要时可额外生成 `项目简介.md` 或 CodeCV 版本。
- 🎯 按目标岗位调整重点：后端、前端、AI/算法都能写。

## 安装 🛠️

```bash
git clone https://github.com/u7-u7/developer-resume-writer.git ~/.codex/skills/developer-resume-writer
```

重启或刷新 Codex 后即可调用。🚀

## 怎么用

### 根据 Git 项目写项目经历

```text
使用 $developer-resume-writer，根据这个 Git 项目地址帮我写后端简历里的项目经历和项目产出。
```

### 根据本地目录写项目经历

```text
使用 $developer-resume-writer，分析这个本地项目文件夹，生成可直接写进简历的项目简介和项目产出。
```

### 带上你的真实职责一起写

```text
使用 $developer-resume-writer，根据这个项目写项目经历。
我主要负责任务编排、接口设计和异常处理；目标岗位是 Java 后端工程师。
```

## 你会拿到什么 📦

默认生成 `项目经历.md`，格式如下：

```markdown
## <项目名称>

**项目简介**：<项目是什么、解决什么问题、核心能力和技术机制>

**技术栈**：`技术 A`、`技术 B`、`技术 C`

### 项目产出

- **小标题**｜具体动作 + 技术方案 + 可确认结果
```

每条项目产出都是“小标题｜简介”格式，整行不超过 200 字，复制进简历就能用。

## 写得靠谱的小原则

- 先说清项目是什么，再写技术方案和项目产出。
- 你告诉我负责的内容，就用你的贡献视角来写。
- 没有说明个人职责时，先写项目已有能力，并给出你可确认的贡献方向。
- 没有明确数据时，不硬编性能、规模或业务收益。
- 不执行项目、不安装依赖；只读理解代码和文档。

## CodeCV（可选）🎨

需要 CodeCV 版本时直接说一声。Skill 会额外生成 `CodeCV-项目经历.md`，并按 [简约通用模板](https://www.codecvcv.com/jianlimoban/15simple_versatile) 适配。建议设置：主色 `#2F5CC4`、字号 `17`、行距 `15`、上下边距 `22`。

## 项目结构 🗂️

```text
developer-resume-writer/
├── SKILL.md
├── agents/openai.yaml
└── references/
    ├── deliverables.md
    ├── output-contract.md
    └── project-intake.md
```
