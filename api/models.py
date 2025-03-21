from django.db import models

class Customer(models.Model):
    """
    Stores customer information.
    """
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    # You could store address as one field, but to follow the diagram:
    address = models.CharField(max_length=255, blank=True)
    department_number = models.CharField(max_length=50, blank=True)
    building_number = models.CharField(max_length=50, blank=True)
    street_number = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Vendor(models.Model):
    """
    Stores vendor information.
    """
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255, blank=True)
    working_hours = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Menu(models.Model):
    """
    A menu offered by a vendor, which can contain multiple items.
    """
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='menus')
    name = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    """
    Stores individual items (products), each associated with a vendor.
    """
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='items')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Stores categories that belong to a vendor.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.item.name})"


class Order(models.Model):
    """
    Stores orders placed by customers.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # "price_item" is unclear in the diagram, but if needed:
    # price_item = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=50, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Order #{self.pk} by {self.customer.name}"


class Contain(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()


    def __str__(self):
        return f"{self.item.menu.name} contains {self.item.name}"


class Employee(models.Model):
    """
    Stores employees who belong to a vendor.
    """
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='employees')
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} ({self.vendor.name})"


class Manage(models.Model):
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='managers')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='managed_vendors')

    def __str__(self):
        return f"{self.employee.name} manages {self.vendor.name}"


class Delivery(models.Model):
    """
    Tracks deliveries for orders, assigned to employees.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='deliveries')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='deliveries')
    status = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100)
    time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Delivery #{self.pk} for Order #{self.order.pk}"
