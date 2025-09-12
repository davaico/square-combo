from crontab import CronTab

cron = CronTab(user=True)
command = '/home/davaiadmin/apps/square-combo/venv/bin/python -m task.sync_revenue >> /home/davai/apps/square-combo/logs/cron_sync.log 2>&1'

if not any(job.command == command for job in cron):
    job = cron.new(command=command, comment='sync_task_job')
    job.setall('0 6 * * *')  # Every day at 6 AM
    cron.write()
