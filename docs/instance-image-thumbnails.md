# 实例图片缩略图运维

本变更保留已存在的实例主图文件，为列表生成独立缩略图。回填命令默认只预览；只有显式传入 `--execute` 才会写入媒体文件和缩略图字段。命令不会修改或删除原图、`image_version` 或业务字段。

部署代码和数据库迁移后，先检查待处理数量：

```bash
docker compose exec backend python manage.py backfill_fixed_asset_thumbnails
```

确认磁盘空间和预览结果后，分批生成缩略图：

```bash
docker compose exec backend python manage.py backfill_fixed_asset_thumbnails --execute --batch-size 100
```

命令支持 `--limit` 限制本次处理数量，并支持 `--after-id <实例UUID>` 从指定实例后续跑。若中断，先检查命令汇总和最后处理的实例 ID，再用 `--after-id` 继续；已生成的缩略图会自动跳过，可安全重复执行。

完成后再次运行默认预览模式，确认没有待处理图片，并查看失败列表。损坏或不受支持的源图会记录失败并继续处理；这些实例仍使用原图显示，修复源文件后可重新运行命令。

此命令只处理存量回填。后续用户上传会由应用自动保存压缩主图和缩略图。回滚应用代码时不得删除缩略图文件或回滚删除字段；旧代码继续从主图字段读取已有图片。
