# ads/management/commands/setup_state_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from content.models import State, City, Category
from ads.models import Ad
from accounts.models import User
import random

class Command(BaseCommand):
    help = 'Setup sample state-specific data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-states',
            action='store_true',
            help='Create sample states and cities',
        )
        parser.add_argument(
            '--create-ads',
            action='store_true',
            help='Create sample ads for each state',
        )
        parser.add_argument(
            '--ads-per-state',
            type=int,
            default=50,
            help='Number of ads to create per state',
        )

    def handle(self, *args, **options):
        if options['create_states']:
            self.create_states_and_cities()
        
        if options['create_ads']:
            self.create_sample_ads(options['ads_per_state'])

    def create_states_and_cities(self):
        """Create sample states and cities."""
        self.stdout.write('Creating states and cities...')
        
        # Create states
        states_data = [
            {
                'name': 'Illinois',
                'code': 'IL',
                'domain': 'desiloginil.com',
                'meta_title': 'Classified Ads Illinois - Buy & Sell in IL',
                'meta_description': 'Find great deals in Illinois. Buy and sell cars, jobs, real estate, and more.',
                'cities': ['Chicago', 'Aurora', 'Rockford', 'Joliet', 'Naperville', 'Springfield', 'Peoria', 'Elgin']
            },
            {
                'name': 'Texas',
                'code': 'TX',
                'domain': 'desilogintx.com',
                'meta_title': 'Classified Ads Texas - Buy & Sell in TX',
                'meta_description': 'Find great deals in Texas. Buy and sell cars, jobs, real estate, and more.',
                'cities': ['Houston', 'San Antonio', 'Dallas', 'Austin', 'Fort Worth', 'El Paso', 'Arlington', 'Corpus Christi']
            },
            {
                'name': 'Florida',
                'code': 'FL',
                'domain': 'desiloginfl.com',
                'meta_title': 'Classified Ads Florida - Buy & Sell in FL',
                'meta_description': 'Find great deals in Florida. Buy and sell cars, jobs, real estate, and more.',
                'cities': ['Jacksonville', 'Miami', 'Tampa', 'Orlando', 'St. Petersburg', 'Hialeah', 'Tallahassee', 'Fort Lauderdale']
            }
        ]
        
        for state_data in states_data:
            state, created = State.objects.get_or_create(
                code=state_data['code'],
                defaults={
                    'name': state_data['name'],
                    'domain': state_data['domain'],
                    'meta_title': state_data['meta_title'],
                    'meta_description': state_data['meta_description'],
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(f'Created state: {state.name}')
            
            # Create cities for this state
            for i, city_name in enumerate(state_data['cities']):
                city, created = City.objects.get_or_create(
                    name=city_name,
                    state=state,
                    defaults={
                        'is_major': i < 3,  # First 3 cities are major
                        'is_active': True,
                    }
                )
                
                if created:
                    self.stdout.write(f'  Created city: {city_name}')
        
        # Create categories if they don't exist
        categories_data = [
            {'name': 'Jobs', 'icon': '💼', 'sort_order': 1},
            {'name': 'Real Estate', 'icon': '🏠', 'sort_order': 2},
            {'name': 'Cars & Vehicles', 'icon': '🚗', 'sort_order': 3},
            {'name': 'Electronics', 'icon': '📱', 'sort_order': 4},
            {'name': 'Furniture', 'icon': '🪑', 'sort_order': 5},
            {'name': 'Services', 'icon': '🔧', 'sort_order': 6},
            {'name': 'For Sale', 'icon': '🛍️', 'sort_order': 7},
            {'name': 'Community', 'icon': '👥', 'sort_order': 8},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'sort_order': cat_data['sort_order'],
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(f'Created category: {category.name}')

    def create_sample_ads(self, ads_per_state):
        """Create sample ads for each state."""
        self.stdout.write(f'Creating {ads_per_state} ads per state...')
        
        states = State.objects.filter(is_active=True)
        categories = Category.objects.filter(is_active=True)
        
        if not states.exists():
            self.stdout.write(self.style.ERROR('No states found. Run with --create-states first.'))
            return
        
        if not categories.exists():
            self.stdout.write(self.style.ERROR('No categories found. Run with --create-states first.'))
            return
        
        # Create a test user if it doesn't exist
        test_user, created = User.objects.get_or_create(
            email='testuser@example.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'User',
                'is_active': True,
                'email_verified': True,
            }
        )
        
        if created:
            test_user.set_password('testpass123')
            test_user.save()
            self.stdout.write('Created test user: testuser@example.com')
        
        # Sample ad titles and descriptions by category
        ad_templates = {
            'Jobs': [
                ('Software Developer Position', 'Looking for experienced software developer. Remote work available.'),
                ('Marketing Manager Role', 'Join our growing marketing team. Great benefits and salary.'),
                ('Customer Service Rep', 'Part-time customer service position. Flexible hours.'),
            ],
            'Real Estate': [
                ('Beautiful 3BR House', '3 bedroom, 2 bathroom house in great neighborhood.'),
                ('Downtown Apartment', 'Modern apartment in city center. All amenities included.'),
                ('Commercial Space', 'Prime commercial location for rent. High foot traffic.'),
            ],
            'Cars & Vehicles': [
                ('2020 Honda Civic', 'Low mileage, excellent condition. One owner.'),
                ('Ford F-150 Truck', 'Reliable work truck. Well maintained.'),
                ('Toyota Camry Sedan', 'Family car in great condition. Clean title.'),
            ],
            'Electronics': [
                ('iPhone 13 Pro', 'Barely used iPhone in perfect condition. Includes case.'),
                ('Gaming Laptop', 'High-performance gaming laptop. Perfect for work too.'),
                ('Smart TV 55"', 'Large smart TV with all streaming apps.'),
            ],
            'Furniture': [
                ('Dining Room Set', 'Beautiful dining table with 6 chairs. Solid wood.'),
                ('Comfortable Sofa', 'Large sectional sofa. Pet-free, smoke-free home.'),
                ('Office Desk', 'Spacious office desk with drawers. Great condition.'),
            ],
            'Services': [
                ('House Cleaning', 'Professional house cleaning service. Affordable rates.'),
                ('Lawn Care Service', 'Complete lawn care and landscaping services.'),
                ('Tutoring Services', 'Math and science tutoring for all grade levels.'),
            ],
            'For Sale': [
                ('Bicycle for Sale', 'Mountain bike in excellent condition. Rarely used.'),
                ('Kitchen Appliances', 'Various kitchen appliances. Moving sale.'),
                ('Books Collection', 'Large collection of books. Various genres.'),
            ],
            'Community': [
                ('Lost Dog', 'Lost golden retriever in downtown area. Please help find.'),
                ('Garage Sale', 'Multi-family garage sale this weekend. Great deals.'),
                ('Study Group', 'Looking for study partners for certification exam.'),
            ],
        }
        
        total_created = 0
        
        for state in states:
            cities = list(state.cities.filter(is_active=True))
            
            if not cities:
                self.stdout.write(f'No cities found for {state.name}. Skipping.')
                continue
            
            for i in range(ads_per_state):
                category = random.choice(categories)
                city = random.choice(cities)
                
                # Get template for this category
                templates = ad_templates.get(category.name, [('Sample Ad', 'Sample description')])
                title_template, desc_template = random.choice(templates)
                
                # Add some variation to titles
                title = f"{title_template} - {city.name}"
                description = f"{desc_template} Located in {city.name}, {state.name}."
                
                # Random price
                if category.name in ['Jobs', 'Services', 'Community']:
                    price = None
                    price_type = 'contact'
                else:
                    price = random.randint(50, 5000)
                    price_type = random.choice(['fixed', 'negotiable'])
                
                # Random dates (last 30 days)
                days_ago = random.randint(0, 30)
                created_at = timezone.now() - timedelta(days=days_ago)
                expires_at = created_at + timedelta(days=30)
                
                # Random status (mostly approved)
                status = random.choices(
                    ['approved', 'pending', 'draft'],
                    weights=[85, 10, 5]
                )[0]
                
                # Random plan (mostly free)
                plan = random.choices(
                    ['free', 'featured'],
                    weights=[90, 10]
                )[0]
                
                ad = Ad.objects.create(
                    title=title,
                    description=description,
                    price=price,
                    price_type=price_type,
                    condition=random.choice(['new', 'like_new', 'good', 'not_applicable']),
                    user=test_user,
                    category=category,
                    city=city,
                    state=state,
                    status=status,
                    plan=plan,
                    created_at=created_at,
                    expires_at=expires_at,
                    view_count=random.randint(0, 100),
                    contact_count=random.randint(0, 20),
                    favorite_count=random.randint(0, 10),
                )
                
                total_created += 1
                
                if total_created % 50 == 0:
                    self.stdout.write(f'Created {total_created} ads...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {total_created} sample ads!')
        )
