# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-22 19:27
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_auto_20170222_1853'),
    ]

    operations = [
        migrations.RenameField(
            model_name='funcabilitytest',
            old_name='test_link',
            new_name='test_video',
        ),
    ]