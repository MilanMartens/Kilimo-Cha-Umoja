"""Swahili translation for SMS messages using deep-translator (free, no billing required)."""

from deep_translator import GoogleTranslator


def translate_to_swahili(text: str) -> str:
	"""Translate text to Swahili using Google Translate (free via deep-translator).
	
	Args:
		text: The English text to translate.
		
	Returns:
		Translated Swahili text, or original text if translation fails.
	"""
	try:
		translator = GoogleTranslator(source='en', target='sw')
		translated = translator.translate(text)
		return translated if translated else text
	except Exception as e:
		print(f"Translation error: {e}. Using original text.")
		return text
