/* 示例数据 —— 真实数据不随仓库分发。
   生成方式： curl -s https://<你的域名>/api/public/datascreen \
              | python3 scripts/gen-hosts-data.py > hosts_data.js
   大屏启动时优先读 hosts_data.js，缺失则回退到 index.html 里的示例兜底，
   联网状态下两者都会被 API 实时数据覆盖。 */
window.__HOSTS = [
  {"n":"sample-node-1.example.com","p":"湖北省","c":"武汉市","la":30.5833,"lo":114.2669,"r":12.4,"l":0,"on":1},
  {"n":"sample-node-2.example.com","p":"广东省","c":"深圳市","la":22.5429,"lo":114.0596,"r":18.7,"l":0,"on":1},
  {"n":"sample-node-3.example.com","p":"北京市","c":"北京市","la":39.9042,"lo":116.4074,"r":35.2,"l":0,"on":0}
];
