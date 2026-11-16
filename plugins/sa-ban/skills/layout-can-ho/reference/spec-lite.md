# HouseSpec 户型描述格式

设计器启动时用 `planFromSpec()`（项目 `src/model/spec.ts`）把它转成完整方案。
完整例子：`example-spec.json`（由 `example-gen.py` 生成，对应 `example-input.jpg`，效果见 `example-plan2d.png`）。

## 坐标约定

- 单位 **mm**（坐标、墙厚可以写到 0.5mm：奇数墙厚如 245 的中线在半毫米上）；x 向右（东），**y 向下（南）**。原点随意，一般取墙体外轮廓左上角（analyze.py 就是这么取的）。
- 墙坐标是**墙中线**。外墙中线 = 外皮往里缩半个墙厚。
- 墙的端点要落在另一面墙的中线上才算连接。40mm 以内会自动吸附；T 形交接、十字交叉会自动打断。
- 房间不用画：墙围合的区域会自动识别成房间，`rooms` 只是在房间里放一个标签点，用来命名、定材质。

## 结构

```jsonc
{
  "name": "XX小区 3-1201 · 三室两卫",   // 方案名，也用作网页标题
  "height": 2800,                        // 层高
  "phase": "renovate",                   // renovate（默认，可直接布置）| original（原始结构阶段）
  "north": 0,                            // 可选：指北针在图上指的方向，相对图纸上方顺时针多少度（指北针朝上 = 0，朝右 = 90）
  "site": { "city": "上海", "month": 9 },  // 可选：日照模拟的城市（自动查纬度）和月份
  "walls": [
    {
      "a": [x, y], "b": [x, y],          // 中线两端
      "t": 240,                          // 厚度。外墙/承重墙常见 200–240，隔墙 100–120
      "bearing": true,                   // 承重墙（不填时 t ≥ 180 视为承重）
      "flush": "W",                      // 可选：面齐平，见下文
      "openings": [
        { "type": "door", "from": 3620, "to": 4500, "hinge": "from", "into": [4000, 7200] },
        { "type": "window", "from": 5200, "to": 6900, "sill": 900 }
      ]
    }
  ],
  "rooms": [ { "at": [x, y], "name": "主卧", "mat": "walnut", "wallMat": "latexSage" } ],
  "structs": [ { "kind": "sewer", "at": [x, y] } ],
  "beams": [ { "a": [x, y], "b": [x, y], "w": 200, "depth": 400 } ],
  "furniture": [ { "key": "bed18", "at": [x, y], "rot": 90 } ],
  "elec": [ { "kind": "socket", "at": [x, y], "rot": 0 } ],
  "look": { "style": "real", "palette": "plan" }, // 可选：3D 视觉风格与配色，见下文
  "underlay": { "image": "户型图.jpg", "mmPerPx": 17.65, "x": -4413, "y": -1342 }
}
```

### 面齐平 flush

墙中线必须落在节点上才能相连，所以一面薄墙直线接在厚墙后面时（比如 200 厚的外墙段接 100 厚的隔墙），默认两面墙都居中，两侧墙面各错开半个厚度差。
户型图上这种地方通常有一侧是平的（看原图墙线：哪一侧的线是连续的直线）。给**薄的那面墙**写 `"flush": "N" | "S" | "E" | "W"`：
它那一侧的墙面会和同一直线上相接的更厚的墙平齐，节点和连接关系不变。竖直墙填 `E` / `W`，水平墙填 `N` / `S`。
**不写 `flush` 时设计器会自动判断**：交接节点上只有一侧接了垂直的墙（错台被它挡住），薄墙就在**另一侧**（连续墙面、同一个房间那侧）和厚墙平齐；两侧都有 / 都没有垂直墙时判断不了，保持居中——这种地方（外墙中段变薄、十字交叉）对照原图手写 `flush`。确实要居中写 `"flush": "C"`。
这面墙被丁字口打断成几段时，后面一样厚、同一直线的各段会自动跟着平移，整条墙线保持笔直。
房间净尺寸、面积、2D / 3D、靠墙家具都按齐平后的墙面算。设计器里在“原始结构”阶段选中墙，也可以点「X 面齐平 / 居中」切换（整条墙线一起改）。

### 门窗 openings

| 字段 | 说明 |
|---|---|
| `type` | 门：`door` 单开门、`double` 双开门、`unequal` 子母门（大扇 2/3，在 hinge 一端）、`sliding` 推拉门、`folding` 折叠门、`pocket` 隐形推拉门（门扇藏进 hinge 一端的墙里）、`hole` 门洞/垭口、`garage` 车库电动卷帘门（宽 2.4~6m，head 默认 2400，开门时门板卷进门头室内侧的卷帘箱）<br>窗：`window` 平开窗、`slideWindow` 推拉窗、`floorWindow` 落地窗（自带室内护栏）、`highWindow` 高窗、`bay` 飘窗（**往墙外凸出**的那种）<br>隔断：`glassWall` 室内玻璃隔断（固定玻璃，每 ~700 一根竖梃，默认 0/2600；户型图画法：墙的位置上一条细长条、等距分格，常见于茶室 / 书房 / 衣帽间 / 厨房） |
| `from`, `to` | 洞口两端。**水平墙填 x 坐标，竖直墙填 y 坐标**（斜墙填到 a 点的距离）。直接用世界坐标，不用管墙的方向 |
| `hinge` | 门轴在 `from` 端还是 `to` 端（默认 `from`）。看原图门扇那条直线连着洞口哪一端 |
| `into` | 门往哪一侧开：填门扇扫过那一侧的任意一点，一般取门开进去的房间里的一点。不填就开向墙法线正方向 |
| `sill`, `head` | 离地高度 / 洞口顶高。默认：门 0/2100，推拉门、折叠门 0/2400，窗 900/2400，落地窗 0/2500，高窗 1500/2100，飘窗 450/2400 |
| 女儿墙 / 栏板 | 露台女儿墙、楼梯洞口栏板：整段墙开一个 `hole`，`sill` = 栏板高（如 1100），`head` = 层高。设计器会把两头的实墙和转角也只砌到栏板高，漫游时挡人、不算门槛 |
| `entry` | 入户门设为 `true` |
| `bayInner` | 室内飘窗（窗台板凸在墙**内侧**）：`{"type": "bayInner", "from": .., "to": .., "into": [房间里一点], "depth": 500}`，生成时变成窗台 450 的 `window` + 室内一侧一块同宽、450 高的飘窗台（`bayDeck`）。往墙外凸的才用 `bay` |

原图里窗台板画在**墙内侧**（室内一条白色窗台、台面凸进房间）的，用 `bayInner`（自动带 450 高飘窗台）；只是窗台低、没有台面的用 `window` + `sill: 450`；不要用 `bay`（那是往墙外凸的）。
怎么从户型图判断窗型：
- 窗线一直画到地面、通常在客厅/卧室朝阳台或外墙的大面宽 → `floorWindow`
- 窗线里画了两段错开的窗扇 → `slideWindow`；普通三线窗 → `window`
- 卫生间、厨房很窄的窗，或图上虚线画的窗 → `highWindow`
- 厨房、阳台门画成折线 → `folding`；入户门一大一小两扇 → `unequal`

### 房间 rooms

- `at` 必须落在墙围合的区域里面（check.mjs 会报 `labelsOutsideRooms`）。
- `at` 也不要落在 `structs`（管井、柱、烟道）的占地上：自动水电按房间名布点时会认不出这个房间（水井、管井标签尤其要避开里面的 shaft）。
- 「入户花园」按楼内有顶的入户门厅处理（开关装在花园里、有吊顶、地面默认 tile），不当露天花园 / 阳台；真正露天的写「露台」「庭院」。
- 一个区域放多个标签会合并显示（如“客厅 + 餐厅”）。开放空间通常只放一个标签。
- **`area`：图上标的房间面积（㎡）一定写上**（`{"at": [..], "name": "主卧", "area": 14.6}`）。自查按墙面算的净面积逐间对账，差超过 max(0.4㎡, 6%) 报「面积对不上」（墙位置 / 墙厚错了、漏墙）；原图按轴线 / 建筑面积标的，用 `areaTol` 放宽并在交付时说明。
- 两个卧室 / 卫生间 / 书房的标签落在同一个封闭区域，自查报「房间合并」：中间漏了墙、墙没接上，或门写成了洞口。主卧 + 衣帽间、卫生间 + 淋浴这类本来连通的不报。
- `mat` 地面材质。不填时按名字猜：卫/厨 → `bath`，车库 → `epoxy`，庭院/花园 → `paving`，阳台/露台 → `deck`，客餐厅/过道 → `tile`，主卧 → `walnut`，其余 → `oak`。
  可选值：`oak` 橡木、`walnut` 胡桃木、`herring` 人字拼、`tile` 灰白大板、`marble` 米白大理石、`cement` 微水泥、`bath` 防滑砖、`terrazzo` 水磨石、`deck` 户外木塑、`paving` 庭院石材、`grass` 草坪、`epoxy` 环氧地坪（车库）。`deck` / `paving` / `grass` 算室外（没有吊顶、不贴踢脚线）。
- `wallMat` 墙面：`latexWhite`、`latexGrey`、`latexSage`、`latexWarm`、`wallpaper`、`wallTile`、`woodPanel`。卫生间/厨房不填时自动用 `wallTile` 和 300mm 平顶吊顶。
- `ceil` 吊顶：`{ "type": "none" | "flat" | "edge" | "tray" | "float" | "alu" | "wood", "drop": 250, "edgeW": 450, "cove": true, "drop2": 150, "edgeW2": 300, "curtain": 200, "cornice": true, "color": "#f1efea" }`
  - `flat` 平顶整体下吊；`edge` 边吊（四周 edgeW 宽一圈下吊 drop，中间原顶）；`tray` 回字形叠级（外圈 drop/edgeW，第二圈 drop2/edgeW2，中间原顶）；
    `float` 悬浮（中间整块下吊 drop，四周 edgeW 宽一圈高 100 藏灯带）；`alu` 铝扣板集成吊顶（厨卫）；`wood` 木饰面 / 木格栅
  - `cove: true` 做灯槽：设计器**自动沿台阶放 LED 灯带**（plan.elec 里 `kind: "strip"`、`auto: "cove:…"`），跟着吊顶尺寸自动更新、自动挂到房间开关上
  - `curtain` 窗帘盒宽（靠窗那面墙留一条到原顶的槽，0 = 不做）；`cornice` 石膏顶角线
  - 同一个区域有多个标签（客厅 + 餐厅 + 门厅）时，吊顶按**第一个标签**算——每个标签都写同样的 `ceil`
- 局部吊顶造型（餐厅上方方形 / 圆形吊顶、假梁、木格栅片）放家具：`ceilZone`（画轮廓）、`ceilZoneCove`（带一圈灯带）、`ceilZoneRound`、`ceilBeamWood`、`ceilSlats`，
  `h` = 下吊厚度，顶面自动贴在顶棚下；只在顶面图层显示和选中。
- `skirting` 踢脚线：`none` | `wood` | `metal`。
- `lighting` 排灯（无主灯筒灯 / 射灯阵列）：`{"kind": "downlight" | "spot" | "light", "sx": 1200, "sy": 1200, "wall": 600, "fit": "center" | "even", "keepMain": false}`
  sx / sy 横纵间距，wall 离墙面距离；center = 按间距排、整组居中（离墙 ≥ wall），even = 首尾正好离墙 wall、中间均分；keepMain = 还保留沙发区 / 卧室主灯。
- `tile` 自定义铺砖（可选，写了就按砖一块块铺，覆盖 `mat` 的预设纹理；不写的字段用默认值）：
  ```json
  "tile": { "w": 800, "h": 800, "gap": 2, "pattern": "grid", "color": "#e6e1d8", "grout": "#c4beb4", "tex": "marble", "origin": "center" }
  ```
  - `w` / `h` 砖的长宽 mm（常见 300×300、300×600、600×600、600×1200、750×1500、800×800、900×1800；木纹砖 200×1200、150×900）
  - `gap` 灰缝 mm（常见 1~3，仿古砖 3~5）
  - `pattern`：`grid` 直铺对缝、`half` 工字铺（1/2 错缝）、`third` 1/3 错缝、`diag` 斜铺 45°、`herring` 人字拼、`basket` 田字编织、`checker` 双色棋盘（配 `color2`）、`random` 随机错缝（木纹砖）
  - `tex` 砖面纹理：`plain` 素色、`marble` 大理石纹、`stone` 石纹、`wood` 木纹、`terrazzo` 水磨石、`cement` 水泥灰
  - `color` 砖色、`color2` 棋盘第二色、`grout` 缝色
  - `origin`：`center` 房间居中起铺（四周切砖一样大，默认）/ `corner` 左上墙角整砖起铺；`ox` / `oy` 起铺偏移 mm；`rot` 0 或 90

### 结构 structs

`kind`：`column` 柱（400×400）、`shaft` 管井（600×400）、`flue` 烟道（450×350）、`drain` 地漏、`sewer` 马桶下水口。
可填 `w`、`d`、`rot`。原图标了的就画上；马桶下水口一般在马桶中心靠墙一侧，离墙约 300。

### 家具 furniture

`at` 是家具中心。`rot` 是朝向（度）：家具“背面”默认朝北（-y）。
**rot 0 = 背靠北墙、90 = 背靠东墙、180 = 背靠南墙、270 = 背靠西墙**。
放在墙边时：中心离墙内皮 = 深度/2（墙内皮 = 墙中线 ± t/2）。`w` 指左右宽，`d` 指前后深，可以覆盖默认尺寸。

| key | 名称 | 默认 w×d×h |
|---|---|---|
| bed18 / bed15 / bed12 | 双人床 1.8 / 1.5、单人床 1.2 | 1800×2100、1500×2050、1200×2000 |
| bunkBed / crib / tatami | 上下床 / 婴儿床 / 榻榻米 | 1000×2000 / 1250×700 / 2000×2000 |
| nightstand / bedBench | 床头柜（台灯 3D 里可点亮）/ 床尾凳 | 500×420 / 1400×400 |
| wardrobe / dresser / mirror | 衣柜 / 梳妆台 / 穿衣镜 | 2000×600×2400 / 1000×450 / 600×60 |
| cabWardrobe / cabSlide | 定制衣柜 / 推拉门衣柜 | 2400×600 / 2000×650 |
| cabTall / cabBase / cabWall / cabTV | 书柜高柜 / 地柜 / 吊柜 / 悬空电视柜 | 1200×400 / 1600×600 / 1600×350 / 2400×400 |
| desk / officeChair / bookshelf | 书桌 / 办公椅 / 书架 | 1200×600 / 600×600 / 900×350 |
| sofa / lSofa / armchair | 三人沙发 / L 形转角沙发（贵妃位在 rot 0 时的西侧，即局部 -x 端）/ 单人沙发 | 2200×950 / 2800×1700 / 850×850 |
| bendSofa | **异形组合沙发（曲线可调）**：图上沙发是弯的、折角的、蛇形的、带贵妃位的，一律用它照图描：`opt.path` = 座深中线的控制点 `"x,y,座深|x,y,座深|…"`（局部 mm，rot 0 时就是相对 `at` 的偏移；从没有靠背的那一头起，**靠背在走向的左手边**），平滑成曲线、两头圆角收口；`opt.open` = 起点那头不带靠背的长度（贵妃位脚踏）。`w` / `d` 写曲线外轮廓的外包框（生成脚本里算，照抄 `reference/example-gen-furnished.py` 的 `bend_sofa`：按图上家具一比一还原的完整示例），改宽深时整体等比拉伸。2D、3D（连续靠背 + 分块座垫 + 靠垫）、碰撞、通道都按曲线算 | 3200×2200 |
| bendSofa_cornerChaise / bendSofa_roundL / bendSofa_serpentine / bendSofa_crescent | 家具库里现成的几种异形组合沙发：转角弧形沙发（带贵妃）/ 圆角 L 形沙发 / S 形蛇形沙发 / 月牙形沙发（同一种 bendSofa，自带 `opt.path`）。图上的沙发和其中一种一样时直接用这个 key（可加 `opt.flip: true` 左右镜像），不一样再用 `bendSofa` + 自己描的 `opt.path`。属性面板里能切造型、镜像、改贵妃位长度和靠背厚 | 2600×3400 / 3200×2400 / 4200×1900 / 3000×1300 |
| curvedSofa | 弧形沙发：同一套曲线几何，按 w × d 自动生成向北拱起的圆弧（靠背在外侧） | 2600×1100 |
| （直段拼接的组合沙发） | 图上就是几段直沙发拼的：每段一个 `sofa`，拼接处写 `opt.arms`：`left` / `right`（只留局部 -x / +x 端扶手）/ `none` | — |
| coffeeTable / tvCabinet | 茶几 / 电视柜（含电视，3D 里可开关） | 1200×600 / 2000×400 |
| diningTable / chair / sideboard | 餐桌 / 餐椅 / 餐边柜 | 1600×900 / 460×520 / 1600×400×2200 |
| kitchenIsland / barStool | 中岛台 / 吧椅 | 1800×900 / 400×400 |
| shoeCabinet / entryBench / piano | 鞋柜 / 换鞋凳 / 立式钢琴 | 1200×350 / 900×350 / 1500×600 |
| rug / plant | 地毯 / 绿植 | 2000×1700 / 500×500 |
| counter / fridge / fridgeDouble | 整体橱柜（含水槽灶台烟机）/ 冰箱 / 对开门冰箱 | 2100×600 / 700×700 / 910×720 |
| hood / microwave / dishwasher / tallOven / purifier | 油烟机（挂墙）/ 微波炉 / 洗碗机 / 电器高柜 / 台下净水器 | 900×520 / 480×380 / 600×600 / 600×600 / 400×200 |
| acWall / acFloor | 挂机空调（离地 2150）/ 柜机空调 | 900×260 / 520×380 |
| waterHeater / gasHeater | 电热水器（离地 1800）/ 燃气热水器（离地 1400） | 800×450 / 360×180 |
| waterDispenser / airPurifier / robotVac / treadmill | 饮水机 / 空气净化器 / 扫地机器人基站 / 跑步机 | 320×330 / 380×250 / 380×420 / 800×1800 |
| wallTV | 壁挂电视（离地 850，3D 里可开关） | 1450×60 |
| floorLamp / deskLamp | 落地灯 / 台灯（3D 里可点亮；台灯默认 z 750 放桌上） | 400×400 / 250×250 |
| curtain / sheer | 落地窗帘 / 纱帘（3D 里可开合）：rot 让背面朝窗，w 比窗宽 200~400 | 2400×160 / 2400×120 |
| toilet / vanity / mirrorCabinet | 马桶 / 浴室柜（含镜）/ 镜柜（挂墙） | 400×700 / 800×500 / 800×150 |
| shower / showerScreen / bathtub | 淋浴房 / 一字淋浴隔断 / 浴缸 | 900×900 / 1200×80 / 1600×750 |
| towelWarmer / bathHeater | 电热毛巾架（挂墙）/ 风暖浴霸（吸顶，自动贴顶） | 500×100 / 300×300 |
| washer / dryer / laundrySink / clothesRack | 洗衣机 / 烘干机 / 洗衣池柜 / 升降晾衣架（吸顶） | 600×600 / 600×620 / 700×550 / 2400×450 |
| lounge / sideTable / island | 休闲椅 / 边几 / 衣帽岛台 | 700×750 / 500×500 / 1200×600 |
| bed20 / roundBed | 双人床 2.0m / 圆床 | 2000×2200 / 2200×2200 |
| chest / fileCabinet / coatRack / stool | 五斗柜 / 文件柜 / 衣帽架 / 圆凳化妆凳 | 900×480 / 450×550 / 500×500 / 400×400 |
| lDesk / kidsDesk / gamingChair / bayCushion | L 形书桌 / 儿童学习桌 / 电竞椅 / 飘窗垫 | 1600×1400 / 1000×600 / 700×700 / 1800×500 |
| loveseat / uSofa / curvedSofa / chaise | 双人沙发 / U 形沙发 / 弧形沙发 / 贵妃椅 | 1600×900 / 3200×2000 / 2600×1100 / 1700×750 |
| beanbag / ottoman / rockingChair / hangingChair | 懒人沙发 / 圆脚凳 / 摇椅 / 吊椅 | 900×900 / 550×550 / 700×950 / 1000×1000 |
| roundCoffee / roundTable / longTable / booth / diningBench | 圆茶几 / 圆餐桌 / 8 人长餐桌 / 卡座 / 餐凳 | 900 / 1300 / 2400×1000 / 1800×600 / 1400×350 |
| ovalTable / ovalCoffee | 椭圆餐桌（6~8 人，椅子围着放）/ 椭圆茶几（户型图上画成椭圆的桌子用它，别拿圆桌或长方桌代替） | 2400×1100 / 1300×800 |
| wineCabinet / displayCabinet / consoleTable / hallCabinet | 酒柜 / 玻璃展示柜 / 玄关桌 / 玄关柜（中空） | 900×450 / 1000×400 / 1200×350 / 1200×400 |
| fireplace / fishTank / projScreen / speaker / screenDivider | 电壁炉 / 鱼缸 / 投影幕布（挂墙）/ 落地音箱 / 屏风 | 1400×400 / 1200×450 / 2400×80 / 300×350 / 1800×40 |
| bigPlant / smallPlant / hangingPlant / floorVase | 大型绿植 / 小盆栽 / 吊兰（吸顶）/ 落地花瓶 | 800 / 300 / 400 / 350 |
| wallPanel | 墙面造型板：`opt.style` = `slat` 木格栅 / `flat` 平板 / `soft` 软包。床头背景墙、电视背景墙、整面护墙板都用它（户型图画法：贴墙一条细带，格栅画等距短刻度、软包 / 平板画双线），rot 让背面贴墙，d 照图上的厚度 | 2400×60×2600 |
| wallArt / wallArt3 / wallClock | 装饰画 / 三联装饰画 / 挂钟（都挂墙） | 900×40 / 1500×40 / 400×50 |
| roundRug / doormat / fan / radiator | 圆地毯 / 门口地垫 / 落地扇 / 暖气片 | 2000 / 900×600 / 400 / 1000×100 |
| lCounter / freezer / trashBin / fridgeFrench | L 形橱柜（长边靠背墙，短边在左）/ 冰柜 / 垃圾桶 / 法式多门冰箱 | 2400×1800 / 1000×600 / 300 / 830×700 |
| uCounter / cabCorner / cabShoe / cabSideboard | U 形橱柜 / L 形转角衣柜 / 中空鞋柜 / 餐边柜 | 2700×2100 / 2400×1800 / 1200×350 / 1800×400 |
| riser / acOutdoor / louver / meterBox | 立管 Φ110 通高 / 空调室外机 / 百叶 / 井道表箱 | 110×110 / 850×320 / 1000×60 / 500×160 |
| cornerShelf / modularSofa / bayDeck | 斜角开放格（`opt.shelves`、`opt.corner`）/ 模块沙发（`opt.n` 格数、`opt.ottoman`）/ 室内飘窗台 450 高 | 450×450 / 2700×1000 / 1800×550 |
| plushToy / tableVase / bookSet | 毛绒玩偶 / 桌面花瓶 / 书摆（z 默认 750 放桌上） | 300×250 / 180×180 / 400×220 |
| wallToilet / squatToilet / doubleVanity / pedestalSink | 壁挂马桶 / 蹲便器 / 双盆浴室柜 / 立柱盆 | 380×550 / 450×600 / 1400×550 / 500×450 |
| freeTub / bathShelf | 独立浴缸 / 置物架 | 1700×800 / 600×250 |
| showerSet | 嵌入式恒温淋浴：贴墙包管台 + 三个旋钮（恒温阀 / 切换）+ 一端壁龛 + 墙上顶喷。户型图画法：卫生间墙边一条窄长框，里面**三个小圆**、一端一个带斜线翻盖的小方框，旁边常有花洒小圆和地漏 → 就是它（不是置物架、不是洗衣机）。`d` 照图上框的深度 | 900×200（h 1100） |
| car / suv | 轿车 / SUV（车头朝家具正面 +y，倒车入库让车头朝车库内墙） | 1850×4800 / 1950×4900 |
| evCharger | 壁挂充电桩（z 1100，自带 `socketEV` 充电桩电源） | 300×150 |
| carport / carport2 | 车棚 单车位 / 双车位（立柱 + 阳光板顶，底下可以再放车） | 3200×5600 / 6000×5600 |
| garageShelf / workbench / bicycle | 车库储物架 / 工具台 + 洞洞板 / 自行车 | 1800×500 / 1800×650 / 600×1750 |
| pool / lawn / stepStones | 泳池（石材压边 + 水面）/ 草坪块 / 汀步石板路 | 3500×8000 / 4000 / 600×3600 |
| tree / shrub | 庭院乔木 / 灌木球 | 2600（h 4500）/ 900 |
| gazebo / parasol / sunLounger / swing | 凉亭 / 遮阳伞 + 桌椅 / 泳池躺椅 / 庭院秋千 | 3200 / 2800 / 700×1950 / 2000×1300 |
| bbq / waterFeature / fence / gate / lawnLamp | 户外烧烤台 / 叠水景墙 / 庭院围栏 / 庭院大门（放在围墙车道口、人行门上）/ 草坪灯（可点亮，中控里算灯） | 1600×650 / 1600×600 / 2000×60 / 3000×150 / 200 |
| billiards / mahjong / teaTable / theaterSofa | 台球桌 / 自动麻将桌（地插）/ 茶台（带上下水）/ 影院沙发三连座 | 1600×2850 / 950 / 1800×800 / 2600×1000 |
| grandPiano / barCounter / sauna / chandelier | 三角钢琴 / 吧台（带水槽）/ 桑拿房 / 挑空水晶大吊灯（吸顶，挂在所在层顶面） | 1550×1900 / 2400×650 / 1500 / 1200（h 1600） |
| boiler / manifold / waterSoftener | 壁挂炉（地暖 + 热水，带燃气、冷热水）/ 地暖分集水器 / 中央软水机 | 450×350 / 800×120 / 350×450 |
| outdoorSet / plantShelf / bike / yogaMat / catTree / petBed | 户外桌椅（带遮阳伞）/ 花架 / 动感单车 / 瑜伽垫 / 猫爬架 / 宠物窝 | 1600 / 1000×350 / 550×1100 / 610×1830 / 600 / 700×550 |
| ductAC / linearVent / linearVentSide / linearReturn / cassetteAC | 中央空调：风管机内机（吸顶，藏吊顶内）/ 线性下出风口 / 侧出风口（边吊侧面）/ 回风口带检修口 / 天花机四面出风 | 1000×500 / 1500×150 / 1500×60 / 1200×300 / 840 |
| vrfOutdoor / freshAirUnit / thermostat / heatPump / bufferTank / floorHeat | 多联机外机 / 新风主机（吸顶）/ 温控面板 / 空气能热泵外机 / 缓冲水箱 / 地暖盘管示意 | 940×370 / 800×600 / 86 / 1000×400 / 500 / 按房间拉大 |
| centralPurifier / preFilter / dehumidifier | 中央净水机 / 前置过滤器 / 除湿机 | 350×300 / 180×150 / 400×300 |
| ceilLamp / linearPendant / bubblePendant / ceilingFan | 吸顶灯（家具款）/ 线性吊灯 / 泡泡（魔豆）吊灯 / 风扇灯：都吸顶、可点亮 | 600 / 1200×80 / 900 / 1320 |
| gardenLamp / inGround / wallWasher | 庭院灯 2.8m / 地埋灯 / 户外壁灯（可点亮） | 380 / 140 / 160×140 |
| integratedStove / washerTower / builtinFridge / smartToilet / ledMirror / projector | 集成灶 / 洗烘套装叠放 / 嵌入式冰箱 / 智能马桶 / 智能背光浴镜（可点亮）/ 吊装投影仪 | 900×600 / 600×650 / 600×600 / 400×700 / 800×40 / 400×320 |
| hedge / flowerBed / planterBox / palm / bamboo / rock | 绿篱 / 砖砌花坛（带花）/ 木花箱 / 棕榈 / 竹丛 / 景观石 | 2000×600 / 1600×800 / 1000×400 / 2400 / 1500×600 / 1200×800 |
| pergola / outdoorSofa / hammock / kidsSlide / dogHouse / firePit / outdoorSink | 花架廊 / 户外藤编沙发组 / 吊床 / 儿童滑梯 / 狗屋 / 火盆 / 户外洗手池 | 3000 / 2600×2000 / 3000×1000 / 1000×2600 / 800×1000 / 1000 / 600×500 |
| landLawn / landGravel / landPaver / landDeck / landWater / landBed | 场地块（自由轮廓，`opt.outline` 写 "x,y\|x,y…" 局部 mm）：草坪（自带草丛）/ 碎石 / 石材铺装 / 户外木平台（能站上去）/ 水景鱼池 / 花境（自带花） | 按图 |
| laundryCabinet / blinds / wallNiche / grabBar | 阳台洗衣柜（左洗衣机位 + 右台盆 + 通长吊柜，自带水电）/ 百叶帘·卷帘（窗内，z 900）/ 壁龛（带灯带，挂墙）/ 适老安全扶手（挂墙 z 800） | 1400×650×2400 / 1200×60 / 600×60×300 / 600×80 |
| murphyBed / safeBox / toiletCabinet / litterBox | 翻板床（收起状态的柜体，平面虚线画放下后的床位）/ 保险柜 / 马桶上方置物柜（挂墙 z 1300）/ 猫砂盆 | 1500×450×2200 / 400×380 / 600×200 / 550×450 |
| freeModel | 自由造型工作台建的组合模型（`opt.model` 由工作台生成，手写 spec 一般不用） | — |

### 底图 underlay

`build.py` 会把原图打包成底图（默认隐藏，用户可在左侧“户型”面板勾选显示、调透明度）。
`mmPerPx` 是比例，`x`、`y` 是图片左上角的世界坐标（mm）。analyze.py 输出的 draft.json 已经算好；
如果你换了原点，`x = -OX * mmPerPx`，`y = -OY * mmPerPx`（OX、OY 是原点在图上的像素位置）。
可选 `rotate`：图片先顺时针转多少度（0 / 90 / 180 / 270，设计图整体转过方向时用）；EXIF 方向标记会自动摆正，不用写。
用 `rectify.py` 拉正过的图：`image` 写 `rectified.png`，`mmPerPx` / `x` / `y` 照 rectify 打印的写（底图和 spec 坐标严格对齐，叠图和各个对账才准）。

### 尺寸链对账 dims / expectDims（可选，强烈建议写）

check.mjs 按这里逐刻度和模型对数，超差（默认 30mm）进 `report.json` 的 `dimIssues`，图纸自己前后矛盾的进 `dimConflicts`。写法见 `workflow-check.md`：

```jsonc
"dims": [ { "name": "底部分段", "line": "y=11640", "at": [11640, 12250], "from": 0, "segs": [600, 1600, 800], "tol": 30, "ref": "face" } ],   // ref: center 轴线 / face 墙面洞口 / 不写都算
"expectDims": { "left": [240, 3260, 120, 2480, 240], "top": [ ... ] }
```

### 批注与待确认 comments / bearingFrom / heightFrom / unsure（可选）

识图拿不准的地方，在设计器右侧「批注」页逐条列给用户确认（作者显示“识图待确认”）：

```jsonc
"comments": [ { "at": [x, y], "text": "这段玻璃图上看不出窗台高，按 900 建的" } ],
"heightFrom": "estimated",                          // 层高是估的：自动加一条批注
"walls": [ { "a": [..], "b": [..], "t": 240, "bearing": true, "bearingFrom": "inferred" } ],   // 推断的承重：属性栏“待确认”+ 批注
"openings": [ { "type": "floorWindow", "from": 100, "to": 2300, "unsure": "窗台高图上没标，按 0 落地建" } ]
```

- `bearingFrom: "drawing"` = 图上画明了；`"inferred"` = 推断（承重的自动加批注）；不写 `bearing` 的墙按厚度推断，属性栏也标“待确认”（不加批注）。
- 栏板洞口：`hole` + `sill ≥ 900` 不写 `head` 时默认开到层高（只砌栏板）；这种洞口不参与通道检查。
- 小于 0.6㎡ 但写了名字的区域（弱电井、管井、0.45㎡ 空调位）照样显示名字、算一个空间。


