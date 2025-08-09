from __future__ import annotations

import click
import random
from app.Console.Command import Command


class InspireCommand(Command):
    """
    Laravel-style Inspire command.
    
    This command displays an inspirational quote, similar to Laravel's inspire command.
    """
    
    # Command signature
    signature = 'inspire'
    
    # Command description
    description = 'Display an inspiring quote'
    
    # Inspirational quotes
    quotes = [
        "The way to get started is to quit talking and begin doing. - Walt Disney",
        "The pessimist sees difficulty in every opportunity. The optimist sees opportunity in every difficulty. - Winston Churchill",
        "Don't let yesterday take up too much of today. - Will Rogers",
        "You learn more from failure than from success. Don't let it stop you. Failure builds character. - Unknown",
        "It's not whether you get knocked down, it's whether you get up. - Vince Lombardi",
        "If you are working on something that you really care about, you don't have to be pushed. The vision pulls you. - Steve Jobs",
        "People who are crazy enough to think they can change the world, are the ones who do. - Rob Siltanen",
        "Failure will never overtake me if my determination to succeed is strong enough. - Og Mandino",
        "Entrepreneurs are great at dealing with uncertainty and also very good at minimizing risk. That's the classic entrepreneur. - Mohnish Pabrai",
        "We don't make mistakes, just happy little accidents. - Bob Ross",
        "Code is like humor. When you have to explain it, it's bad. - Cory House",
        "First, solve the problem. Then, write the code. - John Johnson",
        "Experience is the name everyone gives to their mistakes. - Oscar Wilde",
        "In order to write about life first you must live it. - Ernest Hemingway",
        "The most difficult thing is the decision to act, the rest is merely tenacity. - Amelia Earhart",
        "Every strike brings me closer to the next home run. - Babe Ruth",
        "Definiteness of purpose is the starting point of all achievement. - W. Clement Stone",
        "We must balance conspicuous consumption with conscious capitalism. - Kevin Kruse",
        "Life is what happens to you while you're busy making other plans. - John Lennon",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    ]
    
    @click.command()
    def handle(self) -> None:
        """Execute the inspire command."""
        
        quote = random.choice(self.quotes)
        
        self.line("")
        self.info("💡 " + quote)
        self.line("")
    
    def get_random_quote(self) -> str:
        """Get a random inspirational quote."""
        return random.choice(self.quotes)