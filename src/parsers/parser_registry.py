from src.parsers.enhanced_parser import EnhancedParser
from src.parsers.parser_options import ParserOption

class ParserRegistry:
    _parsers = {}

    @classmethod
    def register_parser(cls, option: ParserOption, parser_instance: EnhancedParser):
        cls._parsers[option] = parser_instance

    @classmethod
    def get_parser(cls, option: ParserOption) -> EnhancedParser:
        parser = cls._parsers.get(option)
        if not parser:
            raise ValueError(f"No parser registered for option: {option}")
        return parser

# Initialize and register EnhancedParser
parser = EnhancedParser()
ParserRegistry.register_parser(ParserOption.ENHANCED_PARSER, parser)
