# survey.html 接 Firebase 配置步骤

> 用途：把问卷收集的数据存到 Firebase（云端数据库），受访者扫码填完即自动入库。
> 状态：操作指南 v1 · 2026-05-19
> 原则：数据去标识化（问卷本身已不采集姓名/工号/手机/科室），数据库设为"只能写、不能公开读"，保护受访者隐私。

---

## 〇、你需要准备什么

- 一个 Google 账号（用于登录 Firebase 控制台，免费额度足够本课题）
- 大约 15 分钟

---

## 一、创建 Firebase 项目

1. 浏览器打开 https://console.firebase.google.com/ ，用 Google 账号登录
2. 点「**创建项目 / Add project**」
3. 项目名称填：`wuhui-research-survey`（或任意，自己认得即可）
4. 「是否启用 Google Analytics」——**选不启用（关掉）**，本课题用不到，能少收集信息更好
5. 点「创建」，等十几秒完成

## 二、创建数据库（Firestore）

1. 左侧菜单找到「**构建 / Build → Firestore Database**」
2. 点「**创建数据库 / Create database**」
3. 模式选「**以生产模式启动 / Start in production mode**」（先锁死，下面第四步再放开"只写"权限）
4. 位置（location）选离中国近的，如 `asia-east1`（台湾）或 `asia-northeast1`（东京），点启用

## 三、添加网页应用、拿到配置

1. 回到项目首页（点左上角项目名）
2. 在「项目概览」页，点页面中间的 **`</>`（Web）图标**——意思是"添加 Web 应用"
3. 应用昵称填 `survey`，**不要**勾"Firebase Hosting"，点「注册应用」
4. 这一步会显示一段 `firebaseConfig = { ... }` 的代码，**就是它**，形如：

   ```js
   const firebaseConfig = {
     apiKey: "AIzaSy....",
     authDomain: "wuhui-research-survey.firebaseapp.com",
     projectId: "wuhui-research-survey",
     storageBucket: "wuhui-research-survey.appspot.com",
     messagingSenderId: "1234567890",
     appId: "1:1234567890:web:abcdef...."
   };
   ```
5. **把这六行值复制下来**（或截图发我，我帮你填进 survey.html）

> ⚠️ 这段配置里的 apiKey 不是密码、可以放进网页（Firebase 设计如此），真正的安全靠第四步的"安全规则"。

## 四、设置安全规则（关键——只许写、不许公开读）

1. 回到「Firestore Database」→ 顶部标签「**规则 / Rules**」
2. 把规则框里内容**整段替换**为下面这段：

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /survey_responses/{doc} {
         allow create: if true;       // 任何人可提交问卷
         allow read, update, delete: if false;  // 任何人都不能读/改/删
       }
     }
   }
   ```
3. 点「**发布 / Publish**」

这样：受访者能提交，但**没有人能从前端读到/篡改/删除**已交数据。课题组看数据要从 Firebase 控制台后台看（见第六步）。

## 五、把配置填进 survey.html

打开 `survey.html`，找到顶部这一段（约第 280 行附近）：

```js
var FIREBASE_CONFIG = {
  apiKey: "PLACEHOLDER_API_KEY",
  ...
};
```

把每个 `PLACEHOLDER_...` 换成第三步拿到的真实值即可。
**或者**：把第三步那六行值发我，我帮你填好并 commit。

`FIRESTORE_COLLECTION` 保持 `"survey_responses"` 不用改（要和第四步规则里的名字一致）。

## 六、怎么看收回来的数据

- Firebase 控制台 → Firestore Database → 数据 / Data 标签 → `survey_responses` 集合，每条 = 一份问卷
- 后续 results.html（待做）会做自动统计图表；导出分析可在控制台导出或用 results 页

## 七、验证是否生效

1. 配置填好后，本地或 GitHub Pages 打开 survey.html，完整填一遍提交
2. 看到"提交成功"且**没有**出现"测试模式：Firebase 未配置"字样 = 接通了
3. 去 Firebase 控制台 Firestore 看是否多了一条记录

---

## 待办

- [ ] 吴慧创建 Firebase 项目并取得 firebaseConfig 六项值
- [ ] 填入 survey.html（自行替换或交 Claude 代填）
- [ ] 发布只写安全规则
- [ ] 提交一条测试数据验证打通，验证后删除该测试记录
- [ ] 确认 Firebase 服务器位置符合数据合规要求（如院方对数据出境有要求，需评估）
