# Playwright 学习笔记

> 边学边记:用于巩固复习。新知识点会持续补充到本文档(追加新小节或更新已有小节)。

## 目录

1. [pytest:运行与配置](#一pytest运行与配置)
2. [有头 / 无头模式](#二有头--无头模式)
3. [Page Object 模式](#三page-object-模式)
4. [定位器 Locators](#四定位器-locators)
5. [expect 断言](#五expect-断言)
6. [工具](#六工具)
7. [调试排查方法](#七调试排查方法)
8. [踩坑记录](#八踩坑记录)
9. [测试运行方式与报告](#九测试运行方式与报告)
10. [Flaky 测试专题](#十flaky-测试专题)
11. [进阶练习路线](#十一进阶练习路线)
12. [常用命令速查表](#十二常用命令速查表)

---

## 一、pytest:运行与配置

- **运行测试的推荐命令**:`python -m pytest tests/smoke_test.py -v`
  - `python -m pytest`:`-m` 以"模块方式"运行 pytest,同时把**当前目录加入 sys.path**(这决定了 `pages` 包能否被导入)
  - `tests/smoke_test.py`:位置参数,指定跑哪个文件;也可以是目录 `tests/`,或精确到用例 `文件.py::用例名`
  - `-v`:verbose 详细模式,显示每个用例名和 PASSED/FAILED;不加只显示 `.`
- **`pytest` 与 `python -m pytest` 的区别**:裸跑 `pytest` 不会把项目根目录加进 sys.path → `ModuleNotFoundError: No module named 'pages'`;`python -m pytest` 会(也可以用下面第 3 条的配置补上)
- **pytest 配置必须写在 `[tool.pytest.ini_options]` 表里**——写在 `[project]` 表下会被**静默忽略**(不报错但不生效):

  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["."]                      # 把项目根加入 sys.path,解决 pages 导入(需 pytest>=7)
  testpaths = ["tests"]                   # 默认只扫描 tests 目录
  addopts = "-v --headed --slowmo=2000"   # 默认参数,任何方式跑 pytest 都生效
  ```

- **VSCode 测试面板**:`.vscode/settings.json` 配 `python.testing.pytestEnabled: true`、`pytestArgs` 等;**改配置后要点面板刷新按钮**(面板有缓存,不自动感知变化)
- **▶ 运行按钮不走 pytest**:它执行 `python 文件路径`,pytest 配置对它无效,而且测试函数只会被"定义"、不会被执行
- 其他常用参数:`-s`(不吞掉 print 输出)、`-k "关键字"`(按名字筛选用例)、`-q`(安静模式)、`--headed`(有头)、`--slowmo=毫秒`(放慢)

### fixture 原理与 conftest.py(依赖注入)

- **fixture = 夹具**:测试前的固定准备步骤(登录、造数据等),pytest 负责执行并把结果注入测试
- **核心机制:依赖注入,按名字匹配**。pytest 读测试函数的参数名 → 找同名 fixture → 执行 → 返回值当实参调用测试(外部函数调用内部函数):

  ```python
  # 你写的:
  def test_backpack_price(inventory_page):   # 参数名 = fixture 名
      ...

  # pytest 内部等价于:
  result = inventory_page_fixture(page)   # ① 先执行同名 fixture
  test_backpack_price(result)             # ② 返回值注入参数,调用测试
  ```

- **fixture 的 Python 语法本质:装饰器 + 注册表**(无需魔法):
  - `@pytest.fixture(scope="session")` 是普通装饰器,等价于 `func = pytest.fixture(scope="session")(func)`——两层调用:工厂(传配置返回装饰器)→ 装饰器(把函数按名字登记进 pytest 全局注册表,原样返回)
  - **你从不直接调用 fixture 函数**——pytest 主循环按测试参数名查注册表,找到被登记的函数,替你调用,再把返回值注入测试参数(你只负责"点名",不负责"调用")
  - 完整故事:装饰器登记 → 测试点单(参数名)→ pytest 查表 → 递归解析依赖 → 调用 fixture 函数 → 返回值缓存 → 注入测试
- ⚠️ **fixture 不会因为"被定义"就自动执行**——必须**被请求**才跑,三种请求方式:① 测试函数参数写了它 ② 其他 fixture 的参数依赖它(依赖链拉起)③ `autouse=True`(真正的无条件自动)。实验验证:定义一个没人用的 fixture 加 print,跑测试不会打印。时机细节:session 级 fixture 在**第一个需要它的测试前**跑,不是 pytest 进程启动瞬间;`delete_output_dir` 是 autouse 的(必跑),`storage_state` 是被依赖链拉起的(有测试用 page 才跑)
- **`page` 也是 fixture**(pytest-playwright 插件注册的),所以参数必须叫 `page` 才会注入
- **fixture 之间可互相依赖**:`inventory_page` 自己声明参数 `page`,pytest 递归解析执行
- **scope 决定执行次数**:`function`(默认,每个测试执行一次 → 每个测试拿全新页面,隔离性好)/ `session`(整个会话一次,共享但可能互相污染)
- **fixture 执行顺序三规律**:
  1. **顺序由依赖关系决定,与定义顺序无关**——pytest 按依赖链递归解析,谁被依赖谁先跑(依赖链越深越先)
  2. **S(session)一次缓存复用,F(function)每测试一次**——所以 7 个测试 = 登录 1 次(storage_state 是 S)+ 每测试开新页面(page 是 F)
  3. **teardown 逆序执行**(栈结构):后 setup 的先拆,先 setup 的最后拆
  - 同名覆盖技巧:定义 `browser_context_args(browser_context_args, ...)` 时,参数解析到的是**插件原版**,不会无限递归——pytest 官方扩展机制
  - **自查工具**:`pytest --setup-plan`(不跑测试只看 fixture 计划)/ `--setup-show`(边跑边显示 SETUP/TEARDOWN)——顺序有疑问直接跑,不用猜
- **`yield` 分两段**:yield 前 = setup(测试前执行);yield 后 = teardown(测试后清理)
- **`conftest.py` 会被 pytest 自动加载,无需 import**,同目录及子目录的测试自动可见其中的 fixture——公共夹具仓库的约定位置
- ⚠️ **conftest 自动加载的是"fixture 注册",不是"名字注入"**:fixture 按参数名注入(测试参数 `inventory_page` 不用 import);但 conftest 里 import 的类名(`InventoryPage` 等)只对 conftest.py 自己可见——测试文件里做**类型注解**或实例化时,照样要自己 `from pages.xxx import XxxPage`,否则 `NameError`。Python 模块命名空间隔离的规则不变;类型注解是可选的,但正规做法是"写注解 + 该 import 就 import"
- **fixture 该返回哪个页面?返回"大多数测试的起点状态"**:测试 90% 从登录后的 inventory 页开始 → 返回 InventoryPage;其他页面由测试从起点自己走过去(调用页面方法),不要每个页面都写 fixture;专门测登录页的测试直接用 `page` 参数自己构造
- 标准写法示例:

  ```python
  # conftest.py(项目根目录)
  @pytest.fixture
  def inventory_page(page: Page) -> InventoryPage:
      login = LoginPage(page)
      login.load()
      login.login(USERNAME, PASSWORD)
      inv = InventoryPage(page)
      inv.verify_inventory_page()
      return inv
  ```

- **return 版 vs yield 版:要不要 teardown?**
  - `return` 是 `yield` 的特例:只有 setup 没有 teardown;两者注入机制一样,区别只在"测试结束后还有没有事要干"
  - **判断标准:fixture 创建了需要"归还/删除/关闭"的东西吗?** 有 → `yield` + 清理;没有 → `return`
  - 经典欠账场景:造了测试数据测完要删(创建测试用户 → 测试 → 删除);占用共享资源要还(开事务 → 测试 → 回滚)
  - **Playwright 场景**:浏览器/页面生命周期由插件自带的 `page` fixture 管理(它内部就是 yield:开浏览器 → 注入页面 → 关浏览器),所以自己的登录类 fixture 纯属"导航+填表"状态准备,零资源占用 → `return` 正确,加 yield 反而多余
  - **teardown 是 try/finally 语义**:测试无论成败,yield 之后的代码都会执行(失败也能收拾现场);但 setup 阶段抛异常时 teardown 不执行

### 测试拆分与参数化

- **拆分前提**:fixture 默认 `function` scope → 每个测试全新浏览器+重新登录,完全隔离,随便拆、随便单跑
- **拆分原则**:
  - 一个测试只验证一件事,测试名说清楚"场景 + 预期"(如 `test_add_product_updates_cart_badge`)
  - 测试间允许少量重复(比如都先加购),**不要为了消除 2 行重复去搞"加购 fixture"**——过度抽象比重复更难维护
  - 多个测试共用的数据提为**模块级常量**(`PRODUCT = "Sauce Labs Backpack"`)
  - 测试里要构造"下一站"页面对象时,用 `inventory_page.page`(BasePage 存的 page)传给新页面类
- **参数化**:同一逻辑、不同数据 → `@pytest.mark.parametrize("参数名1, 参数名2", [(数据1, 数据2), ...])`:

  ```python
  @pytest.mark.parametrize("product, price", [
      ("Sauce Labs Backpack", "$29.99"),
      ("Sauce Labs Bike Light", "$9.99"),
  ])
  def test_product_price(inventory_page, product, price):
      actual = inventory_page.get_product_price(product)
      assert actual == price, f"期望 {price},实际 {actual}"
  ```

  - N 组数据 → 自动跑出 N 个测试,单组数据失败能精确定位
- **拆分后自检**:① `pytest -v` 看到 N 个独立 PASSED ② `-k 关键字` 能单跑 ③ 故意改坏一个断言 → 只有对应测试红,其余照绿(故障被隔离)

### pyproject.toml 与 TOML 格式

- **TOML** = Tom's Obvious, Minimal Language,专为配置文件设计(对比:JSON 无注释难读、YAML 缩进敏感)
- **语法两个概念**:
  - 键值对:`key = value`(字符串 `"..."`、整数、布尔、数组 `[...]`);注释用 `#`
  - 表(table):`[表名]` 开新表,**下一个 `[表名]` 之前的所有键值对都属于它**——"addopts 写错表"坑的根源
- **pyproject.toml = Python 项目配置大本营**(PEP 518/621),一个文件取代 setup.py/setup.cfg/pytest.ini 等散落配置
- **表的分工**:`[project]` = 包元数据(名称/版本/依赖,给打包工具);`[tool.xxx]` = 第三方工具命名空间(工具 x 读 `[tool.x]`,如 `[tool.pytest.ini_options]`、`[tool.ruff]`)
- 典型结构:

  ```toml
  [project]
  name = "playwright-practice"
  requires-python = ">=3.12"
  dependencies = []

  [tool.pytest.ini_options]
  pythonpath = ["."]
  testpaths = ["tests"]
  addopts = "-v --headed --slowmo=2000"
  ```

## 二、有头 / 无头模式

- **Playwright 默认无头(headless)**:浏览器在后台运行不弹窗——"看不到页面"是正常现象,不是报错
- `--headed`:显示浏览器窗口;`--slowmo=500`:每个操作间额外停顿 500ms,方便人眼观察(只在有头模式下有意义)
- **Chromium ≠ Chrome**:Chromium 是开源内核项目,Chrome = Chromium + Google 闭源组件(自动更新、部分编解码器等);Playwright 默认用**自带下载的 Chromium 构建版**,不是系统装的 Chrome
- 无头 = 同一个内核(Blink 渲染引擎 + V8 JS 引擎)正常执行,只是不把画面画到屏幕上;对页面行为几乎无差异
- 想用系统装的 Chrome:`p.chromium.launch(channel="chrome")`;pytest 下加 `--browser-channel=chrome`(Edge 用 `msedge`)

## 三、Page Object 模式

- **写页面类前先问三个问题**:
  - 页面**有什么**?(元素)→ `__init__` 里的 locators
  - 用户能**做什么**?(操作)→ 动作方法
  - 测试要**验证什么**?(断言)→ `verify_xxx` 方法
- **`__init__` 是唯一会被自动调用的构造方法**:

  ```python
  # ✅ 写 LoginPage(page) 时,Python 自动创建实例并调用 __init__(self, page)
  login = LoginPage(page)

  # ❌ init_page 是普通方法:page 被当成 self,还缺一个参数
  login = LoginPage.init_page(page)
  # TypeError: LoginPage.init_page() missing 1 required positional argument: 'page'
  ```

- **调用方法必须加括号**:`login.load` 只是"提到"方法对象,不执行;`login.load()` 才是调用
- 动作方法只做事、不断言;断言方法只检查、不做事
- **方法参数化**:一个方法覆盖所有输入,而不是为每个输入复制一个方法:

  ```python
  def add_product_to_cart(self, product_name: str):
      # 调用 add_product_to_cart("Sauce Labs Backpack") 时,
      # product_name 就是 "Sauce Labs Backpack",展开后等价于 has_text="Sauce Labs Backpack"
      self.product_items.filter(has_text=product_name).get_by_role("button", name="Add to cart").click()
  ```

- **假绿(false green)**:断言太弱(比如只查 title),测试绿了但没验证到想验证的东西。检验标准:**故意把被测行为改坏,测试应该变红**。例:登录页和 inventory 页 title 都是 "Swag Labs",只查 title 区分不出在哪一页
- **locator 只在页面类里出现,测试永远不碰**(Page Object 的封装灵魂,面试英文版):
  - 一句话:Locators are encapsulated inside Page Objects — test files never touch them. Tests interact with pages only through public methods.
  - 三理由:maintainability(页面层是 single source of truth,UI 变更只改一处)/ readability(测试读起来像业务步骤,不懂 CSS 也能懂)/ separation of concerns(页面层管 how,测试层管 what)
  - 收尾金句:It's the same encapsulation idea as OOP — implementation details are hidden behind an interface, so changes stay local.
  - 被追问"页面类太大":shared elements(header/footer)放 BasePage 继承,而非复制
  - 测试只通过页面类的公开方法交互(动作/verify/get),**绝不**自己写 `page.locator(...)`,也不访问页面对象的内部 locator 属性
  - 反例(测试伸进页面内部):`inventory_item.product_price.inner_text()` → 应在页面类加 `get_product_price()`,测试调用它
  - 为什么:页面结构变了只改页面类一处;测试读起来像业务步骤,与"怎么找元素"解耦
- **E2E 长用例的拆分原则(一条主线 + 若干专项)**:
  - **E2E 主线不拆碎**:保留一条完整走通的链路用例(验证"整体流程通不通"),内部可有多断言,但每条带清楚报错信息
  - **细节拆成专项**:表单校验(负向)、价格计算、单页元素显示等"想单独跑/单独修"的断言,拆成独立小测试
  - 判断标准:"这个断言失败了,我想单独跑它吗?" 想 → 拆;只是流程一环 → 留主线
  - **"反复登录"的正确解法是技术手段不是大测试**:`storage_state` 存登录态,之后测试免 UI 登录——用技术消除重复,而不是用设计回避重复
  - 拆分收益:失败定位快、可并行、重跑成本低、链路短更稳(flaky 概率是各环节连乘)、维护集中
  - 拆太细的代价(真实存在):前置重复 → 用 fixture/storage_state 消除,而不是不拆
- **前置步骤的 fixture 化(AAA 结构落地)**:
  - 每个测试必须有**独立的前置**(隔离铁律),但重复的前置代码用 **fixture 抽象**,不是每个测试里复制粘贴,也不是让测试互相依赖
  - 结构:Arrange(前置准备)→ 放 fixture;Act(操作)/ Assert(断言)→ 留测试里——**测试只写"本测试独有"的步骤**
  - 示例:详情页测试共享"从 inventory 点进详情页"的前置 → 定义 `product_detail_page` fixture(依赖 inventory_page),测试一行拿页面
  - fixture 放哪三选一:只一个测试文件用 → 定义在该文件内(最内聚);多个文件用 → 根 conftest.py;子目录内共享 → 该目录 conftest.py
  - **判断标准的完整版**:① 前置 ≥2 个测试共享 → 抽 fixture;② 仅 1 个测试用 → 写测试里(宁可少量重复,不过度抽象);③ **前置要在 fixture 动作之前插入** → 退一层,用更基础 fixture 自己排顺序(fixture 在测试体之前执行,来不及插队)——fixture 分层:基础层(通用起点)/ 常见路径层 / 特殊路径自己走
  - 附带收益:魔法值(如 product_id)被关进 fixture,测试不接触页面内部知识
  - **"写的重复"要消,"跑的重复"要留**:fixture 只写一次(代码层),但 function 级每个测试仍各跑一遍(执行层)——这遍"重复跑"就是隔离本身,省掉它测试就开始互相污染
  - **能否连"跑"也省掉的判断标准**:产物是"凭证"(只读,共享无害,如登录态 cookie)→ session 级跑一次;产物是"现场"(可变状态,如页面导航/购物车)→ function 级每测试跑。storage_state(凭证)与 product_detail_page(现场)是这条规则的一正一反两个实例
- **测试文件归属规则:按"被验证行为的主体页面"分**:问"这条用例失败时,坏的是哪个页面?"——如"点击商品链接能跳转到详情页"的主体是 inventory 页(链接/跳转行为),放 inventory 的测试文件;"详情页正确显示价格"的主体是 detail 页,放 detail 文件。归属看**行为主体**,不是"断言写了哪个页面的内容";测试名必须与内容相符(叫 shows_price 就得真断言价格)
- **断言放哪:pages 还是 tests?(职责划分)**:

  | 层 | 用什么 | 断言什么 |
  |---|---|---|
  | pages/ 页面类 | `expect`(verify_xxx 方法) | **页面状态**:"确实在这个页面上吗?关键元素对了吗?" |
  | tests/ 测试 | `assert` | **业务规则**:这次场景关心的数据对不对 |

  - 判断标准:断言是"**这个页面永远成立的事实**" → 页面类;"**这一次测试场景关心的业务规则**" → 测试里
  - 页面类三种方法的分工:**动作方法不断言**、`verify_xxx` 用 expect 查状态、`get_xxx` 只返回数据不判对错
  - 分工示例:

    ```python
    # pages/:取数据 + 页面状态
    def get_product_prices(self) -> list[str]:
        return self.product_prices.all_inner_texts()

    def verify_inventory_page(self):
        expect(self.page).to_have_url(".../inventory.html")
        expect(self.page.locator(".title")).to_have_text("Products")

    # tests/:复用 verify + 判业务规则
    inventory.sort_products("lohi")
    prices = inventory.get_product_prices()
    assert prices == sorted(prices)
    ```

## 四、定位器 Locators

- **CSS 选择器三兄弟**:
  - `#login-button` → id 选择器
  - `.title` → class 选择器(`<span class="title">Products</span>`)
  - `div` → 标签选择器
  - 组合/属性:`input[id='user-name']`、`[data-test='xxx']`
- **data-test 是什么**:`data-*` 是 HTML5 自定义属性,不参与渲染;`data-test` / `data-testid` / `data-cy` 是开发者**专门为自动化测试留的稳定钩子**——改它等于故意让测试挂,所以最稳定
- **定位器优先级**:① `data-testid`(有就用)→ ② `get_by_role`(用户视角)→ ③ id / 稳定 class → ④ 文本 / XPath(最后手段)
- **`get_by_role` 的 `name` 不是 HTML 的 `name` 属性,是"可访问名称"(accessible name)**——用户看到/读屏器读到的标签:

  ```html
  <button id="add-to-cart-sauce-labs-onesie" name="add-to-cart-sauce-labs-onesie">
      Add to cart   ← 可访问名称是按钮文本,不是 name 属性!
  </button>
  ```

  | 元素 | 可访问名称来源 |
  |---|---|
  | button / a | 元素内**文本** |
  | input[type=submit] | `value` 属性(登录按钮 "Login" 就是这么来的) |
  | input 文本框 | 关联的 label 或 placeholder |
  | img | `alt` 属性 |
  | 任意元素 | `aria-label`(最高优先级) |

  - 怎么查:① 页面上可见的文字(直觉)② DevTools → 选中元素 → Accessibility 面板的 Name 字段(权威)③ codegen 的 Pick locator 建议
- **strict mode(严格模式)**:locator 匹配到**多个**元素时,操作/断言直接报错 "resolved to N elements"——locator 必须唯一,Playwright 拒绝猜
- **`filter()` 从一堆相似元素里挑目标**:

  ```python
  self.product_items = page.locator(".inventory_item")            # 6 个卡片
  self.product_items.filter(has_text="Sauce Labs Backpack")       # → 1 个
  ```

  - `has_text="文本"`:子串 + 不区分大小写;`has=locator`:要求内部含指定子元素;`has_not_text=` 取反;可链式叠加
  - ⚠️ 筛选完仍必须唯一:"Sauce Labs" 会中 5 个、"T-Shirt" 会中 2 个 → 传完整独特的名称
- **`exact=True` 只在"按文本找元素"的 API 里有**:`get_by_text`、`get_by_role` 的 `name=`、`get_by_label`、`get_by_placeholder`、`get_by_title`、`get_by_alt_text`;**`locator()`、`filter()`、`to_have_text()` 都没有**
- 语义:默认"**子串 + 不区分大小写**";`exact=True` = "**全串 + 区分大小写**"(两种模式都会规整空白;传正则时忽略 exact):

  ```python
  page.get_by_text("T-Shirt").count()                              # 2(两个名字都含 T-Shirt)
  page.get_by_text("T-Shirt", exact=True).count()                  # 0(没有恰好叫 T-Shirt 的)
  page.get_by_text("Sauce Labs Bolt T-Shirt", exact=True).count()  # 1 ✅
  ```

- `to_have_text` 的匹配规则(与 get_by_text 不同!):传字符串 = **整段匹配** + 自动规整空白 + 默认忽略大小写;大小写用 `ignore_case=False` 控制;子串匹配用 `to_contain_text("...")`

- **链式定位(父子关系)**:locator 可以从另一个 locator 出发往下找:

  ```python
  container.locator(".inventory_item")                  # 容器 → 6 个卡片
  items.filter(has_text=...).get_by_role("button", name="Add to cart")  # 卡片 → 卡片内的按钮
  ```

- **调试定位器两件套**:`count()` 数匹配个数;`all_inner_texts()` 打印所有匹配元素的文本
- **嵌套 DOM 怎么取子元素:选择器会"跳层"**:
  - CSS 选择器默认匹配**任意深度**:`.inventory_item_price` 直接找到全部 6 个价格,中间包装层(description/label/pricebar)不需要写出来
  - 只有"要**某个商品**的价格"时才需要分层,而且只需两层思维:**先定位父(商品卡片),再链式取子(价格)**:

    ```python
    product_item = self.product_items.filter(has_text="Sauce Labs Backpack")   # 父:某个商品
    price = product_item.locator("[data-test='inventory-item-price']").inner_text()  # 子:该商品内的价格
    ```

  - 链式 `.locator()` 的作用 = **收窄搜索范围**:子 locator 只在父元素内部找
  - `inner_text()` 返回可见文本(干净);`text_content()` 返回 DOM 原始文本(可能带空白/隐藏文本)——取值一般用 `inner_text()`
  - ⚠️ Python 标识符不能有连字符:`self.shopping-cart-badge` 是语法错误,必须 `self.shopping_cart_badge`

## 五、expect 断言

- **expect 会自动等待(轮询)**:默认最长 5 秒反复检查,条件满足立刻通过,超时才失败。Python 的 `assert` 只检查一次——网页是异步的,点击后页面还没跳转完,`assert` 必挂(flaky)
- 语法模式:`expect(检查对象).断言方法(期望值)`
- 常见断言:

  | 检查对象 | 方法 | 说明 |
  |---|---|---|
  | page | `to_have_title("...")` | 页面标题 |
  | page | `to_have_url("...")` | 当前 URL(**精确匹配**;登录页/inventory 页区分就靠它) |
  | locator | `to_be_visible()` | 元素可见 |
  | locator | `to_have_text("...")` | 整段匹配(自动规整空白、默认忽略大小写);子串用 `to_contain_text` |
  | locator | `to_have_count(n)` | 匹配到 n 个元素 |

- 失败时打印详细调用日志(实际值、超时、页面状态),比 assert 好排查

### expect vs assert:什么时候用哪个

- **核心区别**:`expect` 自动轮询重试(默认最长 5 秒),适合"现在还不满足、等一下就会满足"的条件;`assert` 立即检查一次,适合"已经确定"的值
- **决策规则**:
  - 断言对象是 **locator 或 page**(页面状态:可见性、文本、URL、标题、数量)→ 用 `expect`
  - 断言对象是**已经取到手的 Python 值**(字符串、列表、数字)→ 用 `assert`
  - 问自己:这个条件"可能现在还没满足,等一会儿会满足"吗?是 → expect;否 → assert
- **正例**:

  ```python
  # 页面状态:点击后 URL 可能还没跳转完、徽标还没更新 → expect(会等)
  expect(self.page).to_have_url("https://www.saucedemo.com/inventory.html")
  expect(self.cart_badge).to_have_text("1")

  # 已经从页面取回来的"快照"数据:拿到手就不变了 → assert
  prices = page.locator(".inventory_item_price").all_inner_texts()
  assert len(prices) == 6
  assert prices == sorted(prices)     # 验证排序结果
  ```

- **反例**:
  - `assert page.locator(".title").inner_text() == "Products"` —— 元素还没渲染时 `inner_text()` 直接抛异常,不会重试 → flaky;应换成 `expect(...).to_have_text()`
  - `expect(login_button.is_visible(), "Login")` —— `expect()` 参数只能是 page/locator/API response,**不能传布尔值**;已算出布尔值就用 assert,或直接 `expect(locator).to_be_visible()`
- **典型工作流**:`expect` 等页面到达某个状态(导航完、元素出现)→ 提取数据(`all_inner_texts()` / `inner_text()`)→ `assert` 验证数据内容。expect 管"时机",assert 管"内容"
- **跳转类测试可完全由 verify(expect)组成,无裸 assert 也符合规范**:expect 失败抛的就是 AssertionError,它就是断言。规范标准是"测试里有没有会失败的检查",不是"有没有 assert 关键字";自检:故意改坏 verify 的期望值看测试会不会红。真正违规的是"只做动作不查任何东西"(假绿)
- **assert 可以带报错信息**(建议每次都写):

  ```python
  assert 条件, "失败时显示的信息"
  assert len(prices) == 6, f"商品数量不对:期望 6 个,实际 {len(prices)} 个"
  # 失败输出:AssertionError: 商品数量不对:期望 6 个,实际 5 个
  ```

  - 习惯:写"期望 X,实际 Y"的 f-string 消息,别只写"错了";只有失败时才求值,无性能开销
  - pytest 即使不写消息也会拆解表达式展示两边的值,但消息提供"业务含义"注解

## 六、工具

- **codegen(代码生成器)**:

  ```bash
  playwright codegen https://www.saucedemo.com/
  ```

  - 打开浏览器手动操作,右侧**实时生成**对应的 Playwright 代码
  - 典型用途:① **找定位器**——工具条 Pick locator 精确悬停到目标元素,看它推荐的 locator ② 录流程当"操作手册"抄步骤
  - ⚠️ 生成代码是线性流水账:**没有断言、没有结构、只录了走的那一条路** → 只做起步参考,最终要重构成 Page Object + 加断言

## 七、调试排查方法

- **排查阶梯(从便宜到强大,按顺序用)**:读报错 → 用眼睛看 → print 探路 → 截图/录像 → trace → page.pause()
- **第 0 步:读懂报错(解决 80% 问题)**
  - **先确认这次报错和上次是不是同一个**:报错类型变了(如 FileNotFoundError → Page.goto TimeoutError),说明问题域已切换,按老思路查必然无解
  - `FAILED` = 断言没满足(看期望 vs 实际);`ERROR` = 代码抛异常(定位器错/变量未定义/语法错)
  - 常见报错速查:

    | 报错关键词 | 说明的问题 |
    |---|---|
    | `strict mode violation: resolved to N elements` | 定位器不唯一 |
    | `resolved to 0 elements` / `not found` | 定位器找不到:拼错/页面没跳转/元素未出现 |
    | `Timeout 5000ms exceeded` | expect 等不到 → 期望的行为没发生 |
    | `TimeoutError ... exceeded`(出现在 `inner_text`/`click`/`fill` 上) | ≈ locator 匹配 **0 个元素**:先核对 locator 拼写(数据属性值、连字符 vs 下划线),而不是怀疑网速 |
    | `expected ... actual ...` | 断言不满足,对比差异 |
    | `AttributeError: has no attribute` | 变量/方法名拼错或没定义 |
    | `ModuleNotFoundError` | 导入路径问题 |

  - 看报错**行号**:哪一行失败 → 是哪个动作/断言的问题,范围缩到一行
  - **Call log 是定位器问题的"第一现场"**:超时类报错会把完整 locator 链原样打印,元素找不到时把链里每个属性值和页面真实值比对,拼错一个字符都藏不住(踩坑实例:`inventory_item` 下划线 vs `inventory-item` 连字符)
- **第 1 步:`--headed --slowmo` 用眼睛看**:页面跳转了吗?点对按钮了吗?卡在哪一步?
- **第 2 步:print 探路 + `-s`**:

  ```python
  print("当前 URL:", page.url)                                    # 我在哪个页面?
  print("匹配数量:", page.locator("[data-test='xxx']").count())   # 找到几个?
  print("文本列表:", page.locator(".xxx").all_inner_texts())      # 找出来的都是啥?
  ```

- **第 3 步:失败截图/录像**:`pytest --screenshot=only-on-failure --video=retain-on-failure`,产物在 `test-results/`
- **trace 在公司里的实战定位**:不是用来"跑"的,是用来"查"的——失败现场的完整取证档案。典型场景:
  1. **CI 失败取证(最主流)**:CI 配 retain-on-failure,失败自动留档,工程师看产物不用本地重跑(很多 CI 失败本地复现不了)
  2. **"本地绿、CI 红"**:trace 的 Console/Network/Metadata 揭示环境差异(慢网络/视口/限流/浏览器版本)
  3. **locator 疑难杂症**:DOM 快照显示 locator 那一刻实际命中什么(strict mode、点错元素、0 元素)
  4. **时序竞态**:时间线精确到毫秒,看"点击发生在加载完成之前"这类 flaky 根因
  5. **跨角色沟通**:trace zip 附在 bug 单里,开发不需要懂测试代码就能看复现路径
  6. **新人接手**:先看 trace 了解旧用例做什么、挂在哪一步
  - 公司工作流:CI 红 → HTML 报告点失败用例 → 附件看 trace → 时间线定位 → 判测试问题(修 locator/时序)还是产品 bug(附 trace 丢给开发)
  - 取证分工:截图=一眼看长相;视频=给非自动化角色看过程;trace=工程师查为什么;HTML 报告=汇总入口
  - **工程注意①:数据脱敏三道防线**——防线 1:测试环境用**假数据/专用账号**(不出现就不用脱,最根本);防线 2:Playwright 层减量(`tracing.start(sources=False)` 关源码、`page.mask(locator)` 像素遮挡、只在关键段开 trace);防线 3:流水线后处理(归档前正则脱敏脚本、CI artifacts 仅内部可见+限权限+短保留期、bug 单放内部链接不外传)。现实优先级:假数据 + 权限 就够大多数团队,金融/医疗才上正则脱敏和遮罩
  - **工程注意②:trace 太大四招**——① 只留失败(retain-on-failure,已砍大头)② CI 归档策略:`if: failure()` 才上传 + `retention-days: 7`(GitHub Actions)/ `expire_in: 7 days`(GitLab),解决 90% 体积 ③ 缩包:sources=False、只在关键段录、**视频与 trace 二选一**(视频最占空间)④ 云端化:传对象存储/S3/测试平台,报告放链接,CI 本机不留
  - **分级取证(敏感场景不开 trace,用代码级替代)**:trace 不是全有或全无,三层各管一件事——`--tracing` 管全局默认(失败才留),代码 `tracing.start/stop` 管粒度(哪段、sources/snapshots 开关),`page.mask()` 和日志 Filter 管隐私:
    - 敏感页面(登录/支付/账户)→ 不开 trace,截图+mask 遮罩,或纯日志
    - 按 marker 选择性开 trace:`request.node.get_closest_marker("trace")` 判断,只给打标记的用例 start/stop
    - 日志脱敏:Python logging 的 `Filter` 类对 record.msg 做正则替换(手机号/卡号→***),比事后解 zip 脱敏优雅
- **第 4 步:trace(时间机器,疑难杂症用)**:

  ```bash
  pytest --tracing=retain-on-failure    # 只保留失败用例的 trace
  playwright show-trace test-results/<测试名>/trace.zip
  ```

  - 能看到:每步操作时间线、每步前后 DOM 快照(当时 locator 实际匹配到了什么)、截图、控制台日志、网络请求
  - 适用场景:前几步看不出原因,尤其是"locator 为什么没匹配上/匹配错了"
- **第 5 步:交互式调试**:代码里插 `page.pause()`,或 `PWDEBUG=1 python -m pytest ...`,弹出 Inspector 逐行执行、实时检查元素
- **第 6 步:二分法缩小范围**:`-k 用例名` 只跑失败用例;注释一半步骤对半切,逐步定位到具体步骤
- ⚠️ 新手误区:跳过前两步直接上 trace——信息量巨大容易晕。报错信息和自己的眼睛永远是最好的 debugger
- **IDE 波浪线 vs 运行时报错(环境配置类问题)**:
  - `Import "pytest" could not be resolved`(Pylance 波浪线)**≠** 运行时报错——是 VSCode 静态检查在说"我用的解释器里没这个库",不影响终端运行
  - 常见原因:VSCode 选中的 Python 解释器和终端跑测试用的**不是同一个**
  - **判断标准:命令行能跑通 → 代码没问题,波浪线只是 IDE 环境没配对**
  - 修复:`Ctrl+Shift+P` → "Python: Select Interpreter" → 选终端跑测试用的解释器(如系统 Python 3.12 路径),Pylance 重新索引后波浪线消失、补全恢复
  - 通用经验:IDE 的补全异常、波浪线、类型报错,先检查"解释器选对了吗"

## 八、踩坑记录

| # | ❌ 错误写法 | ✅ 正确写法 | 原因 |
|---|---|---|---|
| 1 | `login.load` | `login.load()` | 忘括号 → 方法根本没被调用,页面没跳转 |
| 2 | `def init_page(...)` / `LoginPage.init_page(page)` | `def __init__(...)` / `LoginPage(page)` | 只有 `__init__` 是构造方法,会被自动调用 |
| 3 | `get_by_role("button", name="login-button")` | `get_by_role("button", name="Login")` | name 匹配可访问名称(value),不是 id |
| 4 | 直接 `python tests/xx.py` 或点 ▶ 按钮 | `python -m pytest` / VSCode 测试面板 | 直接运行不执行测试,且找不到 `pages` 包 |
| 5 | `addopts` 写在 `[project]` 表下 | 写在 `[tool.pytest.ini_options]` 表下 | pytest 只读自己的表,写错位置静默无效 |
| 6 | 只查 title 验证 inventory 页 | 加 `expect(page).to_have_url("...inventory.html")` | 两页 title 相同,断言太弱 → 假绿 |
| 7 | 裸跑 `pytest`(非 `-m`) | pyproject 配 `pythonpath = ["."]` | 裸跑不把项目根加入 sys.path |
| 8 | addopts 里写光杆 `--tracing` | `--tracing=retain-on-failure` | 它是"必须带值"的参数(合法值 on/off/retain-on-failure),不是无值开关;无值开关(如 `--headed`)才能单独写 |
| 9 | `--html=test-results/report.html` 报 FileNotFoundError(全绿时必挂,有失败反而能跑通!) | **报告别放进 playwright 的输出目录**:改 `--html=reports/report.html` | 真凶是 pytest-playwright 的 autouse session fixture:会话开始时整删 `--output` 目录(默认 test-results)。全绿 → 无产物 → 目录保持被删 → 报告写不进去;有失败 → trace 产物重建目录 → 侥幸成功。hook 建目录无效(顺序在删除之前);pytest-html 4.x 其实自己会建父目录 |
| 10 | `Page.goto: Timeout 30000ms exceeded`(Call log 显示 navigating/waiting until "load") | 重跑验证(`--lf`);规律性出现则调小 --slowmo 或 `goto(wait_until="domcontentloaded")` | 这是**网络/站点层**超时(网站 30 秒没响应),不是定位器问题;免费演示站可能限流 → flaky |
| 11 | 用例"消失了":collect 数量比预期少 1 | 检查函数名是否 `test_` 开头 | pytest 只收集 `test_` 开头的函数,**不报错、静默跳过**;文件名也要 `test_*.py` / `*_test.py` |

---

## 九、测试运行方式与报告

- **按范围挑**:`pytest`(全量)/ `pytest tests/xx.py`(单文件)/ `pytest tests/xx.py::test_xxx`(单用例)
- **按名字/标记过滤**:
  - `-k "cart"` / `-k "cart or price"` —— 用例名子串/逻辑组合
  - **markers 分层**:用例打 `@pytest.mark.smoke` / `@pytest.mark.regression`,pyproject 里注册:

    ```toml
    [tool.pytest.ini_options]
    markers = [
        "smoke: 冒烟测试,快速验证核心流程",
        "regression: 回归测试,全量验证",
    ]
    ```

  - `pytest -m smoke` 只跑冒烟层——测试金字塔的执行层落地:日常跑 smoke(快),发版跑全量
- **失败控制**:`-x`(首败即停)/ `--maxfail=3` / `--lf`(只跑上次失败的,排错神器)/ `--ff`(上次失败的优先)
  - 排错工作流:`--lf` → 修复 → `--lf` 全绿 → 全量回归
- **并行(xdist)**:
  - 用法:`pytest -n auto`(按核数)/ `-n 4`(固定);`--dist` 分发策略:`load`(默认,动态均衡)/ `loadscope`(按文件分组,文件级共享状态时用)/ `loadgroup`(按 `@pytest.mark.xdist_group` 分组)
  - 原理:主进程收集 → 起 N 个独立 worker 子进程 → 分发 → 汇总;**worker 间不共享内存**
  - **能用前提**:① 测试完全独立 ② 数据不冲突 ③ 注意 session 级 fixture 会在每个 worker 各执行一次(4 worker = 登录 4 次;function 级天然安全)④ 只配无头
  - **不能用场景**:有头调试、排查 flaky、测试有顺序依赖、共享唯一资源(端口/文件/账号)、免费第三方站点(请求量倍增易被限流)、用例太少(worker 启动开销反而更慢)
  - **临时覆盖 addopts 并行跑无头**:`pytest -n 2 -o "addopts=--tracing=retain-on-failure --html=reports/report.html --self-contained-html"`;终端 `[gw0]`/`[gw1]` 前缀 = 不同 worker
  - **工程习惯:并行参数不进 addopts**——按场景开关(CI 开、本地关),放 CI 配置或脚本里

### 截图与视频

- **命令行开关(pytest-playwright,零代码)**:
  - `--screenshot on / only-on-failure / off`;`--video on / retain-on-failure / off`
  - ⚠️ 命名差异:截图用 **only-on-failure**,视频用 **retain-on-failure**——意思一样名字不同,易混
  - 产物落 `test-results/<测试名>/`;`only-on-failure`/`retain-on-failure` 是 CI 和日常默认(成功零成本,失败留证据)
- **代码方式(特定时刻抓)**:

  ```python
  page.screenshot(path="screenshots/step1.png", full_page=True)   # full_page=整页长截图
  page.locator("#cart").screenshot(path="screenshots/cart.png")   # 只截某个元素

  context = browser.new_context(record_video_dir="videos/")        # 视频在 context 层开启
  # ...测试动作...
  context.close()   # 关闭时落盘,webm 格式(Chrome 可直接播放)
  ```

  - 典型场景:业务留痕(如"下单成功页截图存证据"),命令行开关做不到
- **与报告联动**:pytest-playwright 自动把截图/视频/trace 作为附件嵌进 pytest-html 报告,失败用例点开可见——"失败现场档案"零配置
- **选择速查**:交互排查→trace;CI 留证→only-on-failure/retain-on-failure;业务留痕→代码 page.screenshot();演示→--video on(临时,勿挂 addopts,录制开销明显)
- **测试报告阶梯**(按投入递增):

  | 层级 | 工具 | 特点 |
  |---|---|---|
  | 终端 | pytest 内置 | `-v`、`--durations=10`(最慢 10 个用例) |
  | JUnit XML | 内置 `--junitxml=test-results/junit.xml` | CI 通用格式(Jenkins/GitLab/Azure 都吃) |
  | HTML | pytest-html(**需单独安装**,非 pytest 内置) | 单文件报告,浏览器看,团队分享 |
  | Allure | allure-pytest + allure CLI(重) | 步骤树、截图附件、历史趋势,大项目用: `pytest --alluredir=...` → `allure serve ...` |
  | Playwright 自带 | trace/截图/录像 | 失败现场取证,可作附件嵌入 HTML/Allure 报告 |

- **工程习惯**:所有产物(报告/截图/录像/trace)统一收进 `test-results/`,并加入 `.gitignore`(报告不进版本库)
- ⚠️ **pytest-playwright 与 pytest-html 的目录冲突(重要!)**:
  - pytest-playwright 注册了一个 `autouse` 的 session fixture,在**会话开始时整目录删除** `--output` 指定的目录(默认 `test-results`)——那是它存放截图/录像/trace 的地盘
  - 所以 **HTML 报告绝不能写进 `test-results/`**:全绿时无产物重建目录,报告写入必挂 FileNotFoundError(有失败时 trace 产物会重建目录,反而侥幸成功——伪装成 flaky!)
  - 正确姿势:报告用独立目录 `--html=reports/report.html`,playwright 产物留 `test-results/`
  - pytest-html 4.x 自己会创建报告文件的父目录;用 `pytest_sessionstart` hook 建目录也拦不住(playwright 的删除发生在 hook 之后)——顺序:configure 建目录 → sessionstart(你的 hook)→ 第一次测试 setup(playwright 删目录)

- **钩子(hook)概念**:函数名固定(如 `pytest_sessionstart`),pytest 在对应生命周期时机自动调用,无需装饰器/import;与 fixture(按名字注入)同属"约定即配置"机制
- **hooks/fixture 能定义在哪**:conftest.py(官方称 local plugin 本地插件,✅)或第三方插件包(pytest-playwright 的 page fixture 就是这么来的,✅);**普通测试文件 test_*.py 里定义无效**(❌)
- **conftest 的目录层级作用域**:每层目录的 conftest 只作用于该目录及子目录;离测试越近优先级越高,子目录可覆盖父目录同名 fixture/hook——公共的放根 conftest,局部的放下层 conftest
- **pytest-html 安装与用法**:

  ```bash
  pip install pytest-html    # 必须先装,不是 pytest 内置
  pytest --html=test-results/report.html --self-contained-html
  # --self-contained-html:把 CSS/JS 内嵌进单个 HTML 文件,直接发给别人也能打开
  ```

- 落地顺序建议:终端 -v + trace → pytest-html → junitxml → allure(大项目再上)

---

## 十、Flaky 测试专题

- **定义**:同一份代码、同样输入,不修改任何东西,多次运行结果时而过、时而失败——关键词:不确定、不可复现
- **根因三分类**:
  1. **测试自身问题(大头)**:时序竞态(动作后立刻 assert,或用 `sleep()` 硬等——机器一慢照样挂)、硬编码超时过短、测试间耦合(共享状态/依赖执行顺序)、测试数据冲突、定位器脆弱(文本/坐标/深 XPath)
  2. **环境问题**:网络抖动、第三方站点限流(踩坑 #10 的 saucedemo goto 超时就是实例)、CI 资源不足、浏览器版本差异
  3. **被测系统问题**:真实偶发 bug(异步任务/缓存)、动画/懒加载等合法异步被错误假设为同步
  - 排查顺序:先查测试时序 → 再查环境 → 最后才怀疑产品有真 bug
- **处理策略:预防 → 发现 → 止血 → 根治**:
  - **预防**:用 `expect` 自动等待禁止 `sleep()`;依赖 Playwright auto-waiting(click 前自动等可见/稳定/可点);测试隔离(function fixture、独立数据、不依赖顺序);稳定定位器(data-testid/role)
  - **发现**:CI 失败重跑统计(标记高频随机失败者);失败现场取证(trace/截图/录像);本地复现(循环跑 `--lf`)
  - **止血**:有限重试(pytest-rerunfailures,`@pytest.mark.flaky(reruns=2)`,**重试上限 1-2 次**,无限重试=藏问题);quarantine 隔离(已知 flaky 用例挪到独立 job,不阻塞主流水线,被看见被跟踪)
  - **根治**:flaky 是要修的 bug,不是"重跑一下";定期收敛 quarantine 列表到零
- **面试答题结构**:定义 1 句 → 根因三分类 → 处理四步(预防/发现/止血/根治)→ 结合真实实例(如 saucedemo goto 超时);加分词:重试上限、quarantine、trace 取证、测试隔离

---

## 十一、进阶练习路线

- **默写重搭的正确姿势**:不要推倒现有项目——开新项目、换站点(the-internet.herokuapp.com 经典练习站)、不抄旧代码从零搭一遍(conftest + base_page + 2-3 页面 + fixture + 拆分测试 + 报告配置),搭完对比旧项目看决策差异
- **第一层:补全 saucedemo**——结账流程(CheckoutPage/OverviewPage/CompletePage 三页面串联)、**总价=单价之和的跨页面断言**、排序验证(zip 逐对比较)、负向用例(密码错/locked_out_user)、CSV/JSON 数据驱动
- **第二层:pytest 进阶**——fixture 依赖链与 session 级、conftest 目录分层(子目录覆盖父目录)、钩子实战(pytest_collection_modifyitems / pytest_runtest_makereport)、pytest-rerunfailures 失败重跑、Allure
- **第三层:Playwright 核心大招(优先级)**:
  - ⭐⭐⭐ **storage_state 登录态复用(公司标配,拆分测试的前提)**:
    - **背景:Playwright 三层结构**——browser(浏览器程序)/ context(独立会话,像隐身窗口,**cookie 存在这一层**)/ page(标签页)。登录态在 context 层,所以存取都得操作 context;而插件默认的 page fixture 不给你建 context 的机会,所以要绕开它
    - **storage_state fixture = "办通行证"**:开一个临时 context → 真实走一遍 UI 登录(cookie 写入这个 context)→ `context.storage_state(path=...)` 把登录态导出成 JSON → 关掉临时 context → 返回文件路径(session 级:全会话办一次证)
    - **browser_context_args fixture = "把证写进开门配方"**:插件建每个测试的 context 前会调用它拿参数字典;同名覆盖插件原版,参数里的同名引用原版;`{**原版字典, "storage_state": 路径}` 字典解包合并(加一味登录态);之后每个测试的 page 一出生就是登录态
    - **`**` 字典解包**:把字典摊开成键值对放进新字典,同键后写的覆盖先写的——Python 合并字典的惯用写法
    - 原理:登录一次,`context.storage_state(path="auth.json")` 把 cookie/localStorage 存成文件;之后 new_context 时注入,免 UI 登录
    - 标准实现(conftest 两段式):

      ```python
      AUTH_FILE = "auth.json"

      @pytest.fixture(scope="session")
      def storage_state(browser) -> str:
          """登录一次存登录态,整个会话只执行一次"""
          context = browser.new_context()          # 用插件给的 browser fixture,自己建 context
          page = context.new_page()
          login = LoginPage(page)
          login.load()
          login.login(USERNAME, PASSWORD)
          context.storage_state(path=AUTH_FILE)     # 存登录态
          context.close()
          return AUTH_FILE

      @pytest.fixture(scope="session")
      def browser_context_args(browser_context_args, storage_state):
          """官方扩展点:插件建 context 前调用,塞进 storage_state → 所有测试的 page 自动是登录态"""
          return {**browser_context_args, "storage_state": storage_state}
      ```

    - 之后业务 fixture 删掉登录三行,直接 `inventory.load()` 进业务页;每个测试省 3-5 秒 UI 登录
    - 注意:① auth.json 敏感 → 加 .gitignore ② 每次会话重新生成,不怕 cookie 过期 ③ 并行时每 worker 登录一次 ④ 兜底:load 后 verify 失败说明登录态失效,可在 fixture 里捕获重新登录
    - 适用范围:cookie/localStorage 登录态 ✅;动态 token/服务端 session 登录 ❌(改用 UI 登录或 API 拿 token)
  - ⭐⭐⭐ page.route 网络拦截(mock 接口/慢网络/拦截图片,UI 测试摆脱后端依赖)
  - ⭐⭐ 等待策略(wait_for_response / expect_navigation)、弹窗多标签页(expect_page / dialog)、上传下载(set_input_files)
  - ⭐ 移动端 --device 模拟、API+UI 混合(APIRequestContext 造数据)
- **第四层:换站点默写重搭**,每搭一个场景练一个 API(iframe/拖拽/动态加载/文件上传/弹窗/多窗口)
- 节奏建议:本周第一层 → 下周 fixture 深化 + storage_state → 之后 the-internet 重搭
- **文件下载控件的验证(expect_download 三层)**:
  - 核心:`page.expect_download()`——⚠️ 必须在**点击之前**注册(下载可能瞬间完成);同步 API:`with page.expect_download() as info:` → `download = info.value`
  - **L1 事件发生**:expect_download 没超时 = 控件确实触发了下载
  - **L2 元数据**:`download.suggested_filename`(文件名)、`download.save_as(tmp_path / "x.pdf")`(存到 pytest 临时目录,自动清理)、`st_size > 0`(非空)
  - **L3 内容校验**(文件是业务交付物时才做):PDF 魔数 `f.read(4) == b"%PDF"` → pypdf 读页数/抽文本验业务字段;CSV/JSON 用对应模块解析
  - 坑:异步生成的文件先 0 字节,大小断言放 `save_as()` **之后**;页面反馈信号(按钮变灰/提示)与下载验证双保险
  - 备选:下载链路怪时退到网络层 `expect_response(lambda r: "pdf" in r.url)` 验 status 200
  - 强度选择:L1+L2 是公司常态;交付物类文件(对账单/合同)才上 L3
- **缺口的三大块(待学)**:
  - **视觉测试(Visual Testing)**:`pytest-playwright-visual` 插件,`assert.snapshot(page.screenshot())` 与基线快照逐像素对比;`mask=[locator]` 屏蔽动态区域、`threshold` 调容差、`--update-snapshots` 更新基线——UI 大厂标配
  - **CI/CD 落地**:GitHub Actions 无头跑 + secrets 管理账号密码,把本地框架接进流水线
  - **认证场景**:storage_state 登录态复用(已在第三层优先级列过,课程有完整演示)

---

## 十二、常用命令速查表

### 跑测试(选择与过滤)

| 命令 | 作用 |
|---|---|
| `pytest` | 全量(按 testpaths 收集) |
| `pytest tests/test_cart.py` | 单文件 |
| `pytest tests/test_cart.py::test_xxx` | 单用例 |
| `pytest -k "cart"` | 按名字过滤(子串、**大小写敏感**,支持 and/or/not) |
| `pytest -k "cart and not remove"` | 组合过滤/反选 |
| `pytest -m smoke` | 按标记过滤(需在 pyproject 注册 markers) |
| `pytest --collect-only` | 只收集不执行(验证收集数量/语法) |

### 跑测试(失败控制与调试)

| 命令 | 作用 |
|---|---|
| `pytest -x` | 首个失败即停 |
| `pytest --maxfail=3` | 失败 3 个停 |
| `pytest --lf` | 只跑上次失败的(排错神器) |
| `pytest --ff` | 上次失败的优先跑 |
| `pytest -s` | 不吞掉 print 输出 |
| `pytest -v` / `-q` | 详细 / 安静模式 |
| `pytest --durations=10` | 显示最慢的 10 个用例 |

### 跑测试(Playwright 专属,pytest-playwright 插件)

| 命令 | 作用 |
|---|---|
| `pytest --headed` | 有头模式(显示浏览器窗口) |
| `pytest --slowmo=500` | 每步操作放慢 500ms |
| `pytest --browser=firefox` | 换浏览器(默认 chromium) |
| `pytest --browser-channel=chrome` | 用系统安装的 Chrome/Edge(msedge) |
| `pytest --device="iPhone 13"` | 移动端视口模拟 |
| `pytest --screenshot=on / only-on-failure / off` | 截图(失败才留推荐) |
| `pytest --video=on / retain-on-failure / off` | 录像(注意和 screenshot 的值名不同!) |
| `pytest --tracing=on / retain-on-failure / off` | trace(失败才留推荐,CI 标配) |
| `pytest --output=artifacts/` | 改产物目录(默认 test-results) |
| `pytest -n auto` | 并行(只配无头,见第九节) |

### 报告

| 命令 | 作用 |
|---|---|
| `pytest --html=reports/report.html --self-contained-html` | HTML 报告(⚠️ 别写进 test-results,playwright 会删) |
| `pytest --junitxml=test-results/junit.xml` | CI 通用 XML 报告 |
| `pytest --alluredir=results && allure serve results` | Allure 报告(重,大项目用) |

### 查看信息与工具

| 命令 | 作用 |
|---|---|
| `pytest --setup-plan` | 不跑测试,只看 fixture 执行计划 |
| `pytest --setup-show` | 边跑边显示 fixture SETUP/TEARDOWN |
| `pytest --trace-config` | 显示生效的插件/配置 |
| `pytest --fixtures` | 列出所有可用 fixture |
| `playwright show-trace test-results` | 打开 trace 时间机器 |
| `playwright codegen <URL>` | 录制操作生成代码/找定位器 |
| `playwright install chromium` | 安装 Playwright 自带浏览器 |

### 常用工作流组合

```bash
# 日常全量:默认 addopts 已带 -v/报告/trace
pytest

# 排错:只跑失败的 + 看 print + 有头放慢
pytest --lf -s --headed --slowmo=500

# 单功能开发:只跑 cart 相关
pytest -k cart

# CI 标准:无头 + 并行 + 失败取证 + 报告
pytest -n auto --tracing=retain-on-failure --screenshot=only-on-failure \
       --junitxml=test-results/junit.xml
```

---

## 更新记录

- 2026-09-12 初版:整理前 12 轮问答的知识点(pytest 配置、有头/无头、Page Object、定位器、expect、工具、踩坑)
- 2026-09-12 补充:第五节新增"expect vs assert:什么时候用哪个"
- 2026-09-12 补充:第三节新增"断言放哪:pages 还是 tests?(职责划分)"
- 2026-09-12 补充:第四节新增"嵌套 DOM 怎么取子元素:选择器会跳层"
- 2026-09-12 补充:第五节新增"assert 带报错信息"
- 2026-09-12 补充:新增第七节"调试排查方法"(排查阶梯、报错速查表、trace 用法)
- 2026-09-12 更正:第四节/第五节关于 exact 的两处错误——to_have_text 没有 exact 参数(用 ignore_case / to_contain_text 替代);exact=True 是"全串 + 区分大小写"(此前误写为"仍忽略大小写"),以本机安装的 Playwright 源码为准
- 2026-09-12 补充:第一节新增"fixture 原理与 conftest.py(依赖注入)"
- 2026-09-12 补充:第三节新增"locator 只在页面类里出现,测试永远不碰(封装原则)"
- 2026-09-12 补充:第七节新增"IDE 波浪线 vs 运行时报错(环境配置类问题)"
- 2026-09-12 补充:第一节新增"pyproject.toml 与 TOML 格式"
- 2026-09-12 补充:新增第九节"测试运行方式与报告"(过滤/标记分层/失败控制/并行/报告阶梯)
- 2026-09-12 补充:踩坑表新增 #8(addopts 光杆 --tracing 未带值)
- 2026-09-12 补充:踩坑表新增 #9;第九节新增"pytest-html 目录问题与 hook 自动建目录"
- 2026-09-12 补充:第九节新增"pytest-html 安装与用法"(pip install pytest-html + --self-contained-html)
- 2026-09-12 补充:踩坑表新增 #10(Page.goto 导航超时 = 网络/站点问题,flaky 概念);第七节补"先确认报错是否同上次"
- 2026-09-12 补充:新增第十节"Flaky 测试专题"(定义/根因三分类/预防发现止血根治/面试答题结构)
- 2026-09-12 更正:踩坑 #9 真相与第九节——FileNotFoundError 真凶是 pytest-playwright 的 autouse fixture 整删 test-results 目录(报告挪到 reports/ 已修复验证);此前"pytest-html 不会建目录"的说法不准确(4.x 会建父目录)
- 2026-09-12 补充:第九节"并行"条目扩展为 xdist 完整说明(分发策略/能用前提/禁用场景/覆盖 addopts 技巧)
- 2026-09-12 补充:第九节新增"截图与视频"(命令行开关/代码方式/报告附件联动/选择速查)
- 2026-09-12 补充:第七节新增"trace 在公司里的实战定位"(六大场景/公司工作流/取证分工/工程注意)
- 2026-09-12 补充:第七节工程注意扩展为完整方案(数据脱敏三道防线/trace 体积四招/CI 归档配置)
- 2026-09-12 补充:第七节新增"分级取证"(敏感场景不开 trace 的代码级替代:marker 选择性开 trace/mask 遮罩/logging Filter 脱敏)
- 2026-09-12 补充:新增第十一节"进阶练习路线"(四层路线:补全 saucedemo/pytest 进阶/Playwright 大招/换站默写重搭)
- 2026-09-12 补充:第十一节新增"缺口的三大块"(视觉测试/CI-CD 落地/认证场景)——对照 Udemy 课程大纲查漏补缺的结果
- 2026-09-13 补充:第十一节新增"文件下载控件的验证"(expect_download 三层验证/常见坑/网络层备选)
- 2026-09-13 补充:第三节新增"E2E 长用例的拆分原则"(一条主线+若干专项/拆分收益/用 storage_state 消除重复)
- 2026-09-13 补充:第十一节 storage_state 条目扩展为完整用法(conftest 两段式/browser_context_args 扩展点/四个注意点/适用范围)
- 2026-09-13 补充:第一节新增"fixture 执行顺序三规律"(依赖决定顺序/S-F 缓存与次数/逆序 teardown/--setup-plan 自查工具)
- 2026-09-13 补充:第十一节 storage_state 条目补充背景(Playwright 三层结构/办证与开门配方两个 fixture 的逐行含义/** 字典解包)
- 2026-09-13 补充:第一节新增"fixture 不会因定义而自动执行"(三种请求方式/autouse 对比/执行时机)
- 2026-09-13 补充:第一节新增"fixture 的 Python 语法本质"(装饰器+注册表/你只点名不调用)
- 2026-09-13 补充:第三节新增"前置步骤的 fixture 化(AAA 结构落地)"(Arrange 进 fixture/测试只写独有步骤/fixture 放置三选一)
- 2026-09-13 补充:第三节新增"写的重复要消,跑的重复要留"(凭证 vs 现场的 scope 选择标准)
- 2026-09-14 补充:第五节新增"跳转类测试可完全由 verify(expect)组成"(expect 就是断言/规范标准是会失败的检查不是 assert 关键字)
- 2026-09-14 补充:第三节新增"测试文件归属规则"(按行为主体页面分文件/测试名与内容相符)
- 2026-09-14 补充:第三节新增"fixture 抽取标准完整版"(独有前置写测试里/需插队时退一层用基础 fixture)
- 2026-09-14 补充:第三节"locator 封装原则"补面试英文表达(一句话版/三理由/收尾金句/被追问话术)
- 2026-09-14 补充:新增第十二节"常用命令速查表"(跑测试/Playwright 专属/报告/查看信息/工作流组合)
