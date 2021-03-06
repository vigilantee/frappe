# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

from rq import Queue, Worker
from frappe.utils.background_jobs import get_redis_conn
from frappe.utils import format_datetime, cint, convert_utc_to_user_timezone
from frappe.utils.scheduler import is_scheduler_inactive
from frappe import _
import hashlib

queue_type = ['background', 'long', 'default', 'short']
bench_hash = hashlib.md5(frappe.utils.get_bench_path().encode("utf-8")).hexdigest()
colors = {
	'queued': 'orange',
	'failed': 'red',
	'started': 'blue',
	'finished': 'green'
}

@frappe.whitelist()
def get_info(show_failed=False):
	conn = get_redis_conn()

	queues = []
	for queue in queue_type:
		queues.append(Queue(bench_hash + "-" + queue, connection=conn))

	workers = []
	for queue in queues:
		workers.extend(Worker.all(queue=queue))

	jobs = []

	def add_job(j, name):
		if j.kwargs.get('site')==frappe.local.site:
			jobs.append({
				'job_name': j.kwargs.get('kwargs', {}).get('playbook_method') \
					or str(j.kwargs.get('job_name')),
				'status': j.status, 'queue': name,
				'creation': format_datetime(convert_utc_to_user_timezone(j.created_at)),
				'color': colors[j.status]
			})
			if j.exc_info:
				jobs[-1]['exc_info'] = j.exc_info

	for w in workers:
		j = w.get_current_job()
		if j:
			add_job(j, w.name)

	for q in queues:
		if q.name != 'failed':
			for j in q.get_jobs(): add_job(j, q.name)

	if cint(show_failed):
		for q in queues:
			if q.name == 'failed':
				for j in q.get_jobs()[:10]: add_job(j, q.name)

	return jobs

@frappe.whitelist()
def get_scheduler_status():
	if is_scheduler_inactive():
		return [_("Inactive"), "red"]
	return [_("Active"), "green"]
