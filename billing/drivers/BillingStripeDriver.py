import stripe
from stripe.error import InvalidRequestError
from billing.exceptions import PlanNotFound
import pendulum

try:
    from config import billing
    stripe.api_key = billing.DRIVERS['stripe']['secret']
except ImportError:
    raise ImportError('Billing configuration found')

class BillingStripeDriver:

    _subscription_args = {}

    def subscribe(self, plan, token, customer=None, **kwargs):
        # create a customer
        if not customer:
            customer = self._create_customer('description', token)

        try:
            subscription = self._create_subscription(customer,
                plan=plan,
                **kwargs
            )
            return subscription['id']

        except InvalidRequestError as e:
            if 'No such plan' in str(e):
                raise PlanNotFound('The {0} plan was not found in Stripe'.format(plan))
            if 'No such customer' in str(e):
                return False
        
        return None

    def trial(self, days=0):
        self._subscription_args.update({'trial_period_days': days})
        return self

    def on_trial(self, plan_id=None):
        try:
            if plan_id:
                subscription = self._get_subscription(plan_id)
                
                if subscription['status'] == 'trialing':
                    return True

                return False
            
        except InvalidRequestError:
            return False
        return None
        
    def is_subscribed(self, plan_id, plan_name=None):
        try:
            # get the plan
            subscription = self._get_subscription(plan_id)
            if subscription['status'] in ('active', 'trialing'):
                return True

        except InvalidRequestError:
            return False
        
        return False
    
    def is_canceled(self, plan_id):
        try:
            # get the plan
            subscription = self._get_subscription(plan_id)
            if subscription['cancel_at_period_end'] is True:
                return True
        except InvalidRequestError:
            return False
        
        return False
    
    def cancel(self, plan_id, now=False):
        subscription = stripe.Subscription.retrieve(plan_id)

        if subscription.delete(at_period_end= not now):
            return True
        return False

    def create_customer(self, description, token):
        customer = self._create_customer('test-customer', 'tok_amex')
        return customer['id']

    def skip_trial(self):
        self._subscription_args.update({'trial_end': 'now'})
        return self

    def _create_customer(self, description, token):
        return stripe.Customer.create(
            description=description,
            source=token # obtained with Stripe.js
        )
    
    def _create_subscription(self, customer, **kwargs):
        if not isinstance(customer, str):
            customer = customer['id']

        for key, value in self._subscription_args.items():
            kwargs[key] = value

        subscription = stripe.Subscription.create(
            customer=customer,
            **kwargs,  
        )
        self._subscription_args = {}
        return subscription
    
    def _get_subscription(self, plan_id):  
        return stripe.Subscription.retrieve(plan_id)