# Jednorázový checklist pro externí IT před ostrým startem

- [ ] repo vlastní organizace Vesna, přístup jen nezbytným osobám;
- [ ] Render a Cloudflare účty vlastní Vesna, MFA zapnuto;
- [ ] PostgreSQL region Frankfurt, `ipAllowList: []`;
- [ ] produkční a restore-test DB jsou různé a restore DB má v názvu `restore`/`test`;
- [ ] R2 bucket má jurisdikci `eu` a není veřejný;
- [ ] R2 token je omezen na backup bucket;
- [ ] Google OAuth redirect přesně `https://evidence.spolekvesna.cz/auth/google/callback`;
- [ ] `ALLOW_LOCAL_LOGIN=false`;
- [ ] silný generovaný `APP_SECRET`;
- [ ] DNS `evidence` směřuje na Render a HTTPS certifikát je validní;
- [ ] databázové migrace proběhly bez chyby;
- [ ] `/health` vrací `ok`;
- [ ] admin/worker/reader role ručně ověřené;
- [ ] první automatická záloha je `ok`;
- [ ] skutečný restore test je `ok`;
- [ ] poslední živý XLSX import prošel nejprve preview;
- [ ] GDPR checklist podepsaně/organizačně uzavřen před prvními reálnými daty.
