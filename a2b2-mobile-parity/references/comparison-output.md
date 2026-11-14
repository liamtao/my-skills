# 对照稿生成与验收

脚本仅整理本地已捕获的证据，不运行产品、不请求API、不修改原图。仅用Python标准库。

```sh
python3 /Users/ben/.agents/skills/a2b2-mobile-parity/scripts/build_comparison.py /absolute/input.json --out /absolute/new-review-directory
```

输出新目录中的`review.html`、`manifest.json`和原图副本。输出目录已有内容时拒绝覆盖；修订使用新目录。输入相对路径相对于输入JSON，输出内资源用相对路径，方便整体携带。

## 输入

```json
{
  "title": "Research 第二批差异确认",
  "context": "同一详情层级；light/en-US；不同账号，仅比较相当空态，不证明数据一致性。",
  "items": [{
    "id": "08b",
    "title": "Pack 详情导航",
    "comparison": "同页同态",
    "status": "待确认",
    "portal": {
      "path": "/absolute/portal-detail.png",
      "source": "实拍",
      "context": "本地Portal，402×874，详情空态，捕获时间…",
      "boxes": [{"label": "1 待改：重复菜单", "x": 2, "y": 1, "w": 15, "h": 7}]
    },
    "ios": {
      "path": "/absolute/ios-detail.png",
      "source": "实拍",
      "context": "iOS模拟器，详情空态，捕获时间…",
      "boxes": [{"label": "1 参考：返回与标题", "x": 0, "y": 3, "w": 95, "h": 8}]
    },
    "changes": [{
      "key": "1",
      "target": "Portal Mobile · Pack详情顶栏",
      "before": "返回、标题之外还有重复菜单入口和占位",
      "after": "顶栏只保留返回＋标题；数量与更新时间位于内容区；列表保持现状",
      "reason": "同层级导航更清晰，采用iOS详情结构"
    }],
    "verification": "列表→详情→返回；菜单/标题不遮挡；内容元数据可见；桌面回归。"
  }]
}
```

`source`只可选：`实拍`、`当前组件 fixture`、`用户提供截图`、`设计示意`、`缺证据`。后两类不作为当前状态已验证的证明。`缺证据`侧使用`path: null`和空boxes，展示明确占位；另一侧仍保留证据。`comparison`明确写同页同态或无法直接比较的具体原因。

坐标是相对于**整张输入图片**的0–100百分比；每个框必须完全落在图片内。局部图用其自身坐标，context说明截取位置并在confirmation链接完整原图。红框标签应简短，目标行为放changes；每个changes.key至少关联一侧框标签，无法标框的缺证据项说明原因。

## 浏览器导出与视觉检查

使用当前环境可用的浏览器打开review.html，按技能的浏览器规范操作；逐卡导出PNG，并在confirmation.md中以绝对路径嵌入。浏览器导出时维持左右并列；窄窗口通过横向滚动查看，不将两端改成上下排列。

生成工具的HTML只是取证呈现。必须再查看导出的每张图片，确认：红框在目标区域；标签可读；同编号与说明一致；图不拉伸/截断；原图或fixture来源明确。脚本的SHA校验只证明副本未改变，不证明截图正确或改法合理。

confirmation.md按编号写“推荐改哪端＋具体结果＋选择状态”，附图和证据边界，避免复制完整代码审计。差异矩阵/契约分析可以另存并链接，审阅者应无需阅读它就能逐项选择。
