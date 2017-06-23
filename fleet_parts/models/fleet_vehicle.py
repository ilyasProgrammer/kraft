# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
import logging
import json
import urllib2
import hashlib
from odoo.tools.translate import _

_logger = logging.getLogger("# " + __name__)
_logger.setLevel(logging.DEBUG)


class TimeOut(Exception):
    pass


class FleetVehicleParts(models.Model):
    _inherit = "fleet.vehicle"

    note = fields.Char(string=u'Название')
    name = fields.Char(compute="_compute_vehicle_name", store=True)
    vin_checked = fields.Boolean('VIN проверен', default=False, help=u'VIN проверен')
    part_line_ids = fields.One2many('fleet.part.line', 'vehicle_id', string=u'Детали')
    prod_date = fields.Integer(u'Дата производства')
    gear = fields.Char(u'Коробка')
    engine = fields.Char(u'Двигатель')
    license_plate = fields.Char(required=False, help='Номер')
    model_id = fields.Many2one('fleet.vehicle.model', u'Модель', required=False, help='Model of the vehicle')
    vin_sn = fields.Char(u'VIN (номер шасси)', copy=False)

    @api.depends('model_id', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = record.note

    @api.multi
    def add_part(self):
        args = str(self._context['uid']) + self.env.cr.dbname + str(self.id) + self.vin_sn
        key = 'test'
        data = hashlib.md5(args + key)
        url = 'http://develop.itbrat.ru:8080/krafto-crawler/frontend/razbor.jsp?uid=%s&db=%s&fleet_id=%s&vin=%s&hash=%s'
        data_hash = data.hexdigest()
        url_arg = (self._context['uid'], self.env.cr.dbname, self.id, self.vin_sn, data_hash)
        return {
            'type': 'ir.actions.act_url',
            'url': url % url_arg,
            'target': 'self',
        }

    @api.one
    def get_price(self):
        data = {
            'uid': self._context['uid'],  # int
            'db': self.env.cr.dbname,  # string
            'fleet_id': self.id  # int
        }
        data = {"id":123,"method":"parts.prices","params": {"ident":"8e0201803l"},"jsonrpc":"2.0"}
        req = urllib2.Request('http://172.16.4.202')
        req.add_header('Content-Type', 'application/json')

        try:
            response = urllib2.urlopen(req, json.dumps(data), timeout=20)
        except urllib2.URLError, e:
            raise TimeOut("There was an error: %r" % e)
        return True

    @api.multi
    def check_vin(self):
        # form button
        self.write({'vin_sn': self.vin_sn, 'name': self.name})
        url = 'http://develop.itbrat.ru:8080/krafto-crawler/frontend/vininfo.jsp?uid=0&db=demo&fleet_id=0&vin=%s&hash=86DEF2B13F7C128462625C239F62055F'
        args = self.vin_sn
        req = urllib2.Request(url % args)
        car = self.env['fleet.vehicle']
        brand = self.env['fleet.vehicle.model.brand']
        car_model = self.env['fleet.vehicle.model']
        try:
            response = urllib2.urlopen(req, timeout=20)
        except urllib2.URLError, e:
            raise TimeOut("There was an error: %r" % e)
        if response:
            data = json.load(response)
            if data.get('error'):
                raise exceptions.Warning('Данный VIN отсутствует в базе.')
            self.write({'vin_checked': True})
            if data['result'].get('engine', False):
                self.engine = data['result']['engine']
            if data['result'].get('transmission', False):
                self.gear = data['result']['transmission']
            if data['result'].get('manufactured', False):
                self.prod_date = int(data['result']['manufactured'])
            if data['result'].get('vehicle', False):
                found_model = car_model.search([('c_id', '=', data['result']['vehicle']['modelId'])])
                if found_model:
                    self.model_id = found_model
        return True


class ProductVehicle(models.Model):
    _inherit = "product.product"

    c_id = fields.Integer('АйДи каталога')
    brandId = fields.Integer('brandId')
    note = fields.Char(u'Примечание')
    oem = fields.Char(u'Артикул')
    secondOem = fields.Char(u'GMNUM артикул')


class VehicleBrand(models.Model):
    _inherit = "fleet.vehicle.model.brand"

    c_id = fields.Integer(u'ID каталога')
    code = fields.Char(u'Код')
    brand = fields.Char(u'Бренд')
    allowVinSearch = fields.Boolean(u'Разрешить поиск по каталогу')
    type = fields.Char(u'Тип')
    parentId = fields.Many2one('fleet.vehicle.model.brand', u'Родитель')

    @api.model
    def sync_brands(self):
        # called by cron
        url = 'http://develop.itbrat.ru:8080/krafto-crawler/frontend/catalogsinfo.jsp?uid=0&db=demo&fleet_id=0&vin=WVWZZZ3BZVP098238&hash=86DEF2B13F7C128462625C239F62055F'
        req = urllib2.Request(url)
        brand = self.env['fleet.vehicle.model.brand']
        try:
            response = urllib2.urlopen(req, timeout=20)
        except urllib2.URLError, e:
            raise TimeOut("There was an error: %r" % e)
        if response:
            data = json.load(response)
            for r in data['result']:
                found = brand.search([('c_id', '=', int(r['id']))])
                if not found:
                    r['c_id'] = int(r['id'])
                    if r.get('parentId', False):
                        found_parent = brand.search([('c_id', '=', int(r['parentId']))])
                        if found_parent:
                            r['parentId'] = found_parent.id
                    new_brand = brand.create(r)
                    self._cr.commit()
                    _logger.info("New brand created: %s", new_brand.name)
                else:
                    found[0].write(r)
                    _logger.info("Old brand found and updated: %s", found.name)


class VehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    c_id = fields.Integer(u'ID каталога')
    modelCode = fields.Char(u'Код модели')

    @api.model
    def sync_models(self):
        # called by cron
        url = 'http://develop.itbrat.ru:8080/krafto-crawler/frontend/modelsinfo.jsp?uid=0&db=demo&fleet_id=0&vin=WVWZZZ3BZVP098238&hash=86DEF2B13F7C128462625C239F62055F'
        req = urllib2.Request(url)
        brand = self.env['fleet.vehicle.model.brand']
        model = self.env['fleet.vehicle.model']
        try:
            response = urllib2.urlopen(req, timeout=20)
        except urllib2.URLError, e:
            raise TimeOut("There was an error: %r" % e)
        if response:
            data = json.load(response)
            for r in data['result']:
                found = model.search([('c_id', '=', int(r['id']))])
                if not found:
                    found_brand = brand.search([('c_id', '=', int(r['brandId']))])
                    r['brand_id'] = found_brand.id
                    r['c_id'] = int(r['id'])
                    model.create(r)
                    self._cr.commit()
                    _logger.info("New model created: %s", r['name'])
                else:
                    found[0].write(r)
                    _logger.info("Old model found and updated: %s", r['name'])
