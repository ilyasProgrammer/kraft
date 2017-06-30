# -*- coding: utf-8 -*-

from odoo import http, api, registry
from odoo.http import request
import json
import urllib2
import logging
import collections
from odoo.addons.web.controllers.main import ensure_db, Home

_logger = logging.getLogger("# " + __name__)
_logger.setLevel(logging.DEBUG)


class FleetPartsAPI(Home):
    # TODO Проверка хеша
    # TODO привязать партнера
    @http.route('/web/load_part', type='http',  auth="public", csrf=False, website=True)
    def load_part(self, uid, db, vin, hash, data):
        # TODO создавать от имени юзера а не судо
        product = request.env['product.template']
        line = request.env['fleet.part.line']
        car = request.env['fleet.vehicle']
        if not data:
            return
        data = json.loads(data)
        found = product.sudo().search([('c_id', '=', data['part']['id'])])
        if not found:
            data['part']['c_id'] = data['part']['id']
            new_product = product.sudo().create(data['part'])
            _logger.info("New product created: %s", new_product.name)
        else:
            found[0].sudo().write(data['part'])
            new_product = found[0]
            _logger.info("Old product found and updated: %s", data['part']['name'])
        request.cr.commit()
        found_line = line.sudo().search([('guid', '=', data['guid'])])
        if not found_line:
            car_to_add_line = car.sudo().search([('vin_sn', '=', vin)])
            vals = {'c_id': data['id'],
                    'product_id': new_product.id,
                    'guid': data['guid'],
                    'partId': data['partId'],
                    'amount': data['amount'],
                    }
            if data.get('type', False):
                vals['type'] = data['type']
            if data.get('rate', False):
                vals['rate'] = data['rate']
            if data.get('price', False):
                vals['price'] = data['price']
            if data.get('description', False):
                vals['description'] = data['description']
            if data.get('sellingRate', False):
                vals['sellingRate'] = data['sellingRate']
            if data.get('weight', False):
                vals['weight'] = data['weight']
            if data.get('volume', False):
                vals['volume'] = data['volume']
            if car_to_add_line:
                vals['vehicle_id'] = car_to_add_line.id
            prices = self.get_price(new_product.oem)
            if not prices.get('error', False):
                if type(prices['result']) is list:
                    for row in prices['result']:
                        for k, v in row:
                            new_price = request.env['fleet.part.price'].sudo().create({'product_id': new_product.id, 'price': v, 'state': k})
                            _logger.info("New price for item %s created: %s" % (new_product.name, v))
                else:
                    for k, v in prices['result'].iteritems():
                        new_price = request.env['fleet.part.price'].sudo().create({'product_id': new_product.id, 'price':v , 'state':k})
                        _logger.info("New price for item %s created: %s" % (new_product.name, v))
            new_line = line.sudo().create(vals)
            _logger.info("New sale item created: %s", new_line.product_id.name)
        else:
            found_line[0].sudo().write(data)
            _logger.info("Old sale item found and updated: %s", data['name'])

        return '{"response": "OK"}'

    @http.route('/web/load_sale_part', type='http',  auth="public", csrf=False, website=True)
    def load_sale_part(self, uid, db, vin, hash, data):
        # TODO создавать от имени юзера а не судо
        product = request.env['product.template']
        line = request.env['fleet.part.line']
        car = request.env['fleet.vehicle']
        if not data:
            return
        data = json.loads(data)
        found = product.sudo().search([('c_id', '=', data['part']['id'])])
        if not found:
            data['part']['c_id'] = data['part']['id']
            new_product = product.sudo().create(data['part'])
            _logger.info("New product created: %s", new_product.name)
        else:
            found[0].sudo().write(data['part'])
            new_product = found[0]
            _logger.info("Old product found and updated: %s", data['part']['name'])
        request.cr.commit()
        found_line = line.sudo().search([('guid', '=', data['guid'])])
        if not found_line:
            car_to_add_line = car.sudo().search([('vin_sn', '=', vin)])
            vals = {'c_id': data['id'],
                    'product_id': new_product.id,
                    'guid': data['guid'],
                    'partId': data['partId'],
                    'amount': data['amount'],
                    }
            if data.get('type', False):
                vals['type'] = data['type']
            if data.get('rate', False):
                vals['rate'] = data['rate']
            if data.get('price', False):
                vals['price'] = data['price']
            if data.get('description', False):
                vals['description'] = data['description']
            if data.get('sellingRate', False):
                vals['sellingRate'] = data['sellingRate']
            if data.get('weight', False):
                vals['weight'] = data['weight']
            if data.get('volume', False):
                vals['volume'] = data['volume']
            if car_to_add_line:
                vals['vehicle_id'] = car_to_add_line.id
            prices = self.get_price(new_product.oem)
            if not prices.get('error', False):
                if type(prices['result']) is list:
                    for row in prices['result']:
                        for k, v in row:
                            new_price = request.env['fleet.part.price'].sudo().create({'product_id': new_product.id, 'price': v, 'state': k})
                            _logger.info("New price for item %s created: %s" % (new_product.name, v))
                else:
                    for k, v in prices['result'].iteritems():
                        new_price = request.env['fleet.part.price'].sudo().create({'product_id': new_product.id, 'price':v , 'state':k})
                        _logger.info("New price for item %s created: %s" % (new_product.name, v))
            new_line = line.sudo().create(vals)
            _logger.info("New sale item created: %s", new_line.product_id.name)
        else:
            found_line[0].sudo().write(data)
            _logger.info("Old sale item found and updated: %s", data['name'])

        return '{"response": "OK"}'

    @http.route('/web/add_vin', type='json', auth="public", methods=['POST'], website=True)
    def add_vin(self, *args, **kw):
        product = request.env['product.template']
        line = request.env['fleet.part.line']
        car = request.env['fleet.vehicle']
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        if kw.get('car_vin', False):
            old_car = car.sudo().search([('vin_sn', '=', kw['car_vin'])])
            if not old_car:
                vals = {'note': kw.get('car_name', False),
                        'partner_id': request.website.partner_id.id,
                        'vin_sn': kw['car_vin']}
                new_car = car.sudo().create(vals)
                _logger.info("New car created. VIN: %s" % kw['car_vin'])
                new_car.check_vin()

    @http.route('/web/load_part_image', type='http',  auth="public", csrf=False, website=True)
    def load_part_image(self, uid, db, vin, hash, data):
        # Add product.product
        product = self.env['product.template']
        if not data:
            return
        for r in data['result']:
            found = product.search([('c_id', '=', r['id'])])
            if not found:
                product.create(r)
                _logger.info("New product created: %s", r['name'])
            else:
                found[0].write(r)
                _logger.info("Old product found and updated: %s", r['name'])
        for r in data['result']['part']:
            found = product.search([('c_id', '=', r['id'])])
            if not found:
                product.create(r)
                _logger.info("New product created: %s", r['name'])
            else:
                found[0].write(r)
                _logger.info("Old product found and updated: %s", r['name'])

        return '{"response": "OK"}'

    @http.route('/web/delete_part', type='http',  auth="public", csrf=False, website=True)
    def delete_part(self, uid, db, vin, hash, data):
        # Add product.product
        product = self.env['product.template']
        if not data:
            return
        for r in data['result']:
            found = product.search([('c_id', '=', r['id'])])
            if not found:
                product.create(r)
                _logger.info("New product created: %s", r['name'])
            else:
                found[0].write(r)
                _logger.info("Old product found and updated: %s", r['name'])
        for r in data['result']['part']:
            found = product.search([('c_id', '=', r['id'])])
            if not found:
                product.create(r)
                _logger.info("New product created: %s", r['name'])
            else:
                found[0].write(r)
                _logger.info("Old product found and updated: %s", r['name'])

        return '{"response": "OK"}'

    @api.model
    def get_price(self, article):
        larticle = article.lower().replace(' ', '')
        url = 'http://services.krafto.local/json-rpc/'
        data = {"id": 1, "method": "parts.prices", "params": {"ident": article}, "jsonrpc": "2.0"}
        req = urllib2.Request(url=url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        try:
            response = urllib2.urlopen(req)
            result = json.load(response)
            return result
        except urllib2.URLError, e:
            return {'error': e}
