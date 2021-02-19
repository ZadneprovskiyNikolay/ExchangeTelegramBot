from datetime import datetime, timedelta
import requests

class Rates: 
    def __init__(self, caching_period_minutes: int): 
        self._rates = None
        self.caching_period_minutes = caching_period_minutes
        self._next_cache_update = datetime.min
        self.update_rates_cache()

    def update_rates_cache(self): 
        """Обновляет кеш котировок если он не обновлялся больше
        'self._caching_period_minutes' минут"""
        if datetime.now() >= self._next_cache_update:                
            resp = requests.get('https://api.exchangeratesapi.io/latest?base=USD')            
            self._rates = resp.json()['rates']    
            self._next_cache_update = datetime.now() + \
                timedelta(minutes=self.caching_period_minutes)   

    def __getitem__(self, key): 
        return self._rates.get(key)

    def items(self): 
        for item in self._rates.items():
            yield item      

    def valid_currency(self, currency: str):             
        return self._rates[currency] is not None