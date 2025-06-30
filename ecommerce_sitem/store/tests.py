from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Product, Order
from .forms import UserRegistration

class ProductModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=10.00,
            stock=100
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(str(self.product), "Test Product")

class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=10.00,
            stock=100
        )
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=2
        )

    def test_order_creation(self):
        self.assertEqual(self.order.user.username, 'testuser')
        self.assertEqual(self.order.product.name, "Test Product")
        self.assertEqual(str(self.order), f"Order {self.order.user} by {self.order.user.username} for {self.order.product.name}")

class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        Product.objects.create(name="Product1", description="Desc1", price=5.00, stock=10)

    def test_home_status_code(self):
        response = self.client.get(reverse('store:home'))
        self.assertEqual(response.status_code, 200)

    def test_home_template(self):
        response = self.client.get(reverse('store:home'))
        self.assertTemplateUsed(response, 'store/home.html')

    def test_home_context(self):
        response = self.client.get(reverse('store:home'))
        self.assertTrue('products' in response.context)
        self.assertEqual(len(response.context['products']), 1)

class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(name="Product1", description="Desc1", price=5.00, stock=10)

    def test_product_detail_valid(self):
        response = self.client.get(reverse('store:product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertEqual(response.context['product'], self.product)

    def test_product_detail_invalid(self):
        response = self.client.get(reverse('store:product_detail', args=[999]))
        self.assertEqual(response.status_code, 404)

class UserRegistrationFormTest(TestCase):
    def test_valid_form(self):
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistration(data=form_data)
        self.assertTrue(form.is_valid())

    def test_duplicate_email(self):
        User.objects.create_user(username='existinguser', email='existing@example.com', password='12345')
        form_data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistration(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class RegisterUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_register(self):
        response = self.client.get(reverse('store:register_user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/register.html')

    def test_post_register_valid(self):
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        response = self.client.post(reverse('store:register_user'), data=form_data)
        self.assertContains(response, 'Please confirm your email address to complete the registration.')

    def test_post_register_invalid(self):
        form_data = {
            'username': '',
            'email': 'invalidemail',
            'password1': '123',
            'password2': '321'
        }
        response = self.client.post(reverse('store:register_user'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/register.html')
        # The error message is rendered as form errors, not as plain text
        self.assertContains(response, 'This field is required.')
        self.assertContains(response, 'Enter a valid email address.')
        self.assertContains(response, 'The two password fields didn’t match.')

class ActivateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='12345', is_active=False)
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_activate_valid(self):
        response = self.client.get(reverse('store:activate', args=[self.uid, self.token]))
        self.assertRedirects(response, reverse('store:login_user'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_activate_invalid(self):
        response = self.client.get(reverse('store:activate', args=[self.uid, 'invalidtoken']))
        self.assertRedirects(response, reverse('store:register_user'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

class LoginUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')

    def test_get_login(self):
        response = self.client.get(reverse('store:login_user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/login.html')

    def test_post_login_valid(self):
        response = self.client.post(reverse('store:login_user'), data={'username': 'testuser', 'password': '12345'})
        self.assertRedirects(response, reverse('store:home'))

    def test_post_login_invalid(self):
        response = self.client.post(reverse('store:login_user'), data={'username': 'testuser', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/login.html')

class LogoutUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_logout(self):
        response = self.client.get(reverse('store:logout_user'))
        self.assertRedirects(response, reverse('store:home'))

class CartViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(name="Product1", description="Desc1", price=5.00, stock=10)

    def test_add_to_cart(self):
        response = self.client.get(reverse('store:add_to_cart', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:cart'))
        session = self.client.session
        self.assertIn(str(self.product.id), session.get('cart', {}))

    def test_cart_view(self):
        session = self.client.session
        session['cart'] = {str(self.product.id): 2}
        session.save()
        response = self.client.get(reverse('store:cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/cart.html')
        self.assertIn('cart_items', response.context)
        self.assertIn('total', response.context)

class CheckoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.product = Product.objects.create(name="Product1", description="Desc1", price=5.00, stock=10)

    def test_checkout_requires_login(self):
        response = self.client.get(reverse('store:checkout'))
        self.assertRedirects(response, f"{reverse('store:login_user')}?next={reverse('store:checkout')}")

    def test_checkout_empty_cart(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('store:checkout'))
        self.assertRedirects(response, reverse('store:cart'))

    def test_checkout_success(self):
        self.client.login(username='testuser', password='12345')
        session = self.client.session
        session['cart'] = {str(self.product.id): 2}
        session.save()
        response = self.client.get(reverse('store:checkout'))
        self.assertRedirects(response, reverse('store:cart'))
        orders = Order.objects.filter(user=self.user, product=self.product)
        self.assertTrue(orders.exists())
        self.assertEqual(orders.first().quantity, 2)
        session = self.client.session
        self.assertEqual(session.get('cart', {}), {})

class SearchViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.product1 = Product.objects.create(name="Apple", description="Desc1", price=5.00, stock=10)
        self.product2 = Product.objects.create(name="Banana", description="Desc2", price=3.00, stock=15)

    def test_search_with_results(self):
        response = self.client.get(reverse('store:search'), {'q': 'Apple'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/search_results.html')
        self.assertIn(self.product1, response.context['products'])
        self.assertNotIn(self.product2, response.context['products'])

    def test_search_no_results(self):
        response = self.client.get(reverse('store:search'), {'q': 'Orange'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/search_results.html')
        self.assertEqual(len(response.context['products']), 0)
