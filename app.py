from flask import Flask, jsonify, redirect, render_template, request, url_for

from db import (
    cancel_order as cancel_order_record,
    clear_table as clear_table_record,
    get_dashboard_data,
    get_menu_items,
    get_table_status as get_table_status_record,
    init_db,
    place_order as place_order_record,
    toggle_item_pay as toggle_item_pay_record,
    toggle_serve as toggle_serve_record,
    update_menu_item,
)

app = Flask(__name__)
init_db()

@app.route('/')
def home():
    return redirect(url_for('guest_menu'))

@app.route('/menu')
def guest_menu():
    return render_template('customer_menu.html', menus=get_menu_items(guest_only=True))

@app.route('/table/<table_id>')
def server_page(table_id):
    return render_template('server_order.html', menus=get_menu_items(), table_id=table_id)

@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html', data=get_dashboard_data())

@app.route('/api/order', methods=['POST'])
def place_order():
    req = request.json
    table_id = str(req.get('table_id'))
    items = req.get('items', [])
    try:
        place_order_record(table_id, items)
        return jsonify({"status": "success"})
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

@app.route('/api/orders', methods=['GET'])
def get_admin_data():
    return jsonify(get_dashboard_data())

@app.route('/api/table_status/<table_id>', methods=['GET'])
def get_table_status(table_id):
    return jsonify(get_table_status_record(str(table_id)))

@app.route('/api/admin/update_menu', methods=['POST'])
def admin_update_menu():
    req = request.json
    update_menu_item(int(req['id']), int(req['price']), int(req['stock']))
    return jsonify({"status": "success"})

@app.route('/api/item_pay', methods=['POST'])
def toggle_item_pay():
    req = request.json
    t_id, idx = str(req.get('table_id')), req.get('order_idx')
    if toggle_item_pay_record(t_id, idx):
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 400

@app.route('/api/serve', methods=['POST'])
def toggle_serve():
    req = request.json
    t_id, idx = str(req.get('table_id')), req.get('order_idx')
    if toggle_serve_record(t_id, idx):
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 400

@app.route('/api/cancel_order', methods=['POST'])
def cancel_order():
    req = request.json
    t_id, idx = str(req.get('table_id')), req.get('order_idx')
    if cancel_order_record(t_id, idx):
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 400

@app.route('/api/clear', methods=['POST'])
def clear_table():
    t_id = str(request.json.get('table_id'))
    if clear_table_record(t_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 400

@app.template_filter('format_price')
def format_price(value):
    return format(value, ',')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
