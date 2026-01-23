import json
import sys


# ---------------- Exceptions ----------------
class InvalidIdException(Exception):
    pass


class InvalidPriceException(Exception):
    pass


# ---------------- Helper functions ----------------
def is_valid_nonnegative_int(value):
    return isinstance(value, int) and (not isinstance(value, bool)) and value >= 0


def validate_nonnegative_int(value, field_name="id"):
    if not is_valid_nonnegative_int(value):
        raise InvalidIdException("Invalid {}: {}".format(field_name, value))


def validate_nonnegative_price(value, field_name="price"):
    if isinstance(value, bool) or (not isinstance(value, (int, float))) or value < 0:
        raise InvalidPriceException("Invalid {}: {}".format(field_name, value))


# ---------------- Data classes ----------------
class Customer:
    def __init__(self, id: int, name: str, city: str, address: str):
        validate_nonnegative_int(id, "id")
        self.id = id
        self.name = name
        self.city = city
        self.address = address

    def __repr__(self):
        return "Customer(id={}, name='{}', city='{}', address='{}')".format(
            self.id, self.name, self.city, self.address
        )


class Supplier:
    def __init__(self, id: int, name: str, city: str, address: str):
        validate_nonnegative_int(id, "id")
        self.id = id
        self.name = name
        self.city = city
        self.address = address

    def __repr__(self):
        return "Supplier(id={}, name='{}', city='{}', address='{}')".format(
            self.id, self.name, self.city, self.address
        )


class Product:
    def __init__(self, id: int, name: str, price: float, supplier_id: int, quantity: int):
        validate_nonnegative_int(id, "id")
        validate_nonnegative_int(supplier_id, "supplier_id")
        validate_nonnegative_int(quantity, "quantity")
        validate_nonnegative_price(price, "price")

        self.id = id
        self.name = name
        self.price = float(price)
        self.supplier_id = supplier_id
        self.quantity = quantity

    def __repr__(self):
        return "Product(id={}, name='{}', price={}, supplier_id={}, quantity={})".format(
            self.id, self.name, self.price, self.supplier_id, self.quantity
        )

    # Needed so we can do sorted(list_of_products) WITHOUT key=lambda
    def __lt__(self, other):
        # Sort by ascending price; break ties by id (deterministic)
        if not isinstance(other, Product):
            return NotImplemented
        if self.price != other.price:
            return self.price < other.price
        return self.id < other.id


class Order:
    def __init__(self, id: int, customer_id: int, product_id: int, quantity: int, total_price: float):
        validate_nonnegative_int(id, "id")
        validate_nonnegative_int(customer_id, "customer_id")
        validate_nonnegative_int(product_id, "product_id")
        validate_nonnegative_int(quantity, "quantity")
        validate_nonnegative_price(total_price, "total_price")

        self.id = id
        self.customer_id = customer_id
        self.product_id = product_id
        self.quantity = quantity
        self.total_price = float(total_price)

    def __repr__(self):
        return "Order(id={}, customer_id={}, product_id={}, quantity={}, total_price={})".format(
            self.id, self.customer_id, self.product_id, self.quantity, self.total_price
        )


# ---------------- System ----------------
class MatamazonSystem:
    def __init__(self):
        self.customers = {}
        self.suppliers = {}
        self.products = {}
        self.orders = {}
        self.next_order_id = 1

    def register_entity(self, entity, is_customer):
        # Must be unique across BOTH customers and suppliers
        validate_nonnegative_int(entity.id, "id")
        if entity.id in self.customers or entity.id in self.suppliers:
            raise InvalidIdException("Invalid id: already exists")

        if is_customer:
            self.customers[entity.id] = entity
        else:
            self.suppliers[entity.id] = entity

    def add_or_update_product(self, product):
        # supplier must exist
        if product.supplier_id not in self.suppliers:
            raise InvalidIdException("Supplier does not exist")

        # new product
        if product.id not in self.products:
            self.products[product.id] = product
            return

        # update existing product: supplier_id cannot change
        existing = self.products[product.id]
        if existing.supplier_id != product.supplier_id:
            raise InvalidIdException("Cannot change supplier_id for existing product")

        existing.name = product.name
        existing.price = product.price
        existing.quantity = product.quantity

    def place_order(self, customer_id, product_id, quantity=1):
        validate_nonnegative_int(customer_id, "customer_id")
        validate_nonnegative_int(product_id, "product_id")
        validate_nonnegative_int(quantity, "quantity")

        if product_id not in self.products:
            return "The product does not exist in the system"

        product = self.products[product_id]

        if quantity > product.quantity:
            # EXACT string (no dot at end)
            return "The quantity requested for this product is greater than the quantity in stock"

        product.quantity -= quantity

        order_id = self.next_order_id
        self.next_order_id += 1

        total_price = product.price * quantity
        order = Order(order_id, customer_id, product_id, quantity, total_price)
        self.orders[order_id] = order

        return "The order has been accepted in the system"

    def remove_object(self, _id, class_type):
        validate_nonnegative_int(_id, "id")
        ct = str(class_type).strip().lower()

        # Check dependencies with plain loops (no any())
        if ct == "customer":
            if _id not in self.customers:
                raise InvalidIdException("Customer id does not exist: {}".format(_id))

            for o in self.orders.values():
                if o.customer_id == _id:
                    raise InvalidIdException("Cannot remove customer with existing orders: {}".format(_id))

            del self.customers[_id]
            return None

        if ct == "product":
            if _id not in self.products:
                raise InvalidIdException("Product id does not exist: {}".format(_id))

            for o in self.orders.values():
                if o.product_id == _id:
                    raise InvalidIdException("Cannot remove product with existing orders: {}".format(_id))

            del self.products[_id]
            return None

        if ct == "supplier":
            if _id not in self.suppliers:
                raise InvalidIdException("Supplier id does not exist: {}".format(_id))

            # supplier dependency: if any order uses a product of this supplier
            for o in self.orders.values():
                p = self.products.get(o.product_id)
                if p is not None and p.supplier_id == _id:
                    raise InvalidIdException("Cannot remove supplier with existing orders: {}".format(_id))

            del self.suppliers[_id]
            return None

        if ct == "order":
            if _id not in self.orders:
                raise InvalidIdException("Order id does not exist: {}".format(_id))

            order = self.orders.pop(_id)

            # restore stock
            p = self.products.get(order.product_id)
            if p is not None:
                p.quantity += order.quantity

            return order.quantity

        raise InvalidIdException("Invalid class_type: {}".format(class_type))

    def search_products(self, query, max_price=None):
        res = []
        for p in self.products.values():
            if p.quantity == 0:
                continue
            if query not in p.name:
                continue
            if max_price is not None and p.price > max_price:
                continue
            res.append(p)

        # No lambda: relies on Product.__lt__
        return sorted(res)

    def export_system_to_file(self, path):
        with open(path, "w", encoding="utf-8") as f:
            for c in self.customers.values():
                print(c, file=f)
            for s in self.suppliers.values():
                print(s, file=f)
            for p in self.products.values():
                print(p, file=f)

    def export_orders(self, out_file):
        # No setdefault: plain loops
        grouped = {}

        for o in self.orders.values():
            p = self.products.get(o.product_id)
            if p is None:
                continue
            s = self.suppliers.get(p.supplier_id)
            if s is None:
                continue

            city = s.city

            if city not in grouped:
                grouped[city] = []
            grouped[city].append(str(o))

        json.dump(grouped, out_file)


# ---------------- Load system ----------------
def load_system_from_file(path):
    sys_obj = MatamazonSystem()

    customers = []
    suppliers = []
    products = []

    safe_globals = {
        "__builtins__": {},  # keep eval minimal
        "Customer": Customer,
        "Supplier": Supplier,
        "Product": Product,
        "Order": Order,
        "InvalidIdException": InvalidIdException,
        "InvalidPriceException": InvalidPriceException,
    }

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            try:
                obj = eval(line, safe_globals, {})
            except (SyntaxError, NameError):
                # illegal lines can be ignored
                continue

            # If constructor raises InvalidIdException/InvalidPriceException -> propagate (do NOT catch)
            if isinstance(obj, Customer):
                customers.append(obj)
            elif isinstance(obj, Supplier):
                suppliers.append(obj)
            elif isinstance(obj, Product):
                products.append(obj)
            else:
                continue

    for c in customers:
        sys_obj.register_entity(c, True)
    for s in suppliers:
        sys_obj.register_entity(s, False)
    for p in products:
        sys_obj.add_or_update_product(p)

    return sys_obj


# ---------------- Script main ----------------
USAGE_MSG = "Usage: python3 matamazon.py -l < matamazon_log > -s < matamazon_system > -o <output_file> -os <out_matamazon_system>"


def _parse_script_args(argv):
    allowed = {"-l", "-s", "-o", "-os"}
    args = {}
    i = 1
    while i < len(argv):
        flag = argv[i]
        if flag not in allowed:
            return None
        if i + 1 >= len(argv):
            return None
        val = argv[i + 1]
        if val in allowed:
            return None
        args[flag] = val
        i += 2
    if "-l" not in args:
        return None
    return args


def _decode_token(tok: str) -> str:
    return tok.replace("_", " ")


def main():
    parsed = _parse_script_args(sys.argv)
    if parsed is None:
        print(USAGE_MSG, file=sys.stderr)
        sys.exit(1)

    try:
        # Load system if provided, else empty
        if "-s" in parsed:
            system = load_system_from_file(parsed["-s"])
        else:
            system = MatamazonSystem()

        # Execute log commands
        with open(parsed["-l"], "r", encoding="utf-8") as logf:
            for raw in logf:
                line = raw.strip()
                if not line:
                    continue
                parts = line.split()
                cmd = parts[0]

                if cmd == "register":
                    who = parts[1].lower()
                    _id = int(parts[2])
                    name = _decode_token(parts[3])
                    city = _decode_token(parts[4])
                    address = _decode_token(parts[5])

                    if who == "customer":
                        system.register_entity(Customer(_id, name, city, address), True)
                    else:
                        system.register_entity(Supplier(_id, name, city, address), False)

                elif cmd == "add" or cmd == "update":
                    pid = int(parts[1])
                    name = _decode_token(parts[2])
                    price = float(parts[3])
                    sid = int(parts[4])
                    qty = int(parts[5])
                    system.add_or_update_product(Product(pid, name, price, sid, qty))

                elif cmd == "order":
                    cid = int(parts[1])
                    pid = int(parts[2])
                    qty = int(parts[3]) if len(parts) >= 4 else 1
                    system.place_order(cid, pid, qty)

                elif cmd == "remove":
                    _id = int(parts[1])
                    class_type = parts[2]
                    system.remove_object(_id, class_type)

                elif cmd == "search":
                    query = _decode_token(parts[1])
                    if len(parts) >= 3:
                        max_price = float(parts[2])
                        res = system.search_products(query, max_price)
                    else:
                        res = system.search_products(query)
                    print(res)

        # Export orders
        if "-o" in parsed:
            with open(parsed["-o"], "w", encoding="utf-8") as out_orders:
                system.export_orders(out_orders)
        else:
            system.export_orders(sys.stdout)

        # Export final system
        if "-os" in parsed:
            system.export_system_to_file(parsed["-os"])

    except Exception:
        print("The matamazon script has encountered an error")
        sys.exit(1)


if __name__ == "__main__":
    main()