"""
Коллекция промптов для виртуальной примерки одежды
"""

# Промпт для валидации результата (можно использовать отдельно)
VALIDATION_PROMPT = """Analyze this try-on result. Answer these questions:
1. Is the person's face the same as in the original photo? (yes/no)
2. Is the background the same as in the original photo? (yes/no)
3. Does the clothing fit naturally on the body? (yes/no)
4. Are there any obvious artifacts or errors? (yes/no)

Provide brief answers."""

# ===== НОВЫЕ ПРОМПТЫ ДЛЯ КОНТРОЛИРУЕМОЙ ПРИМЕРКИ =====

# Промпт для примерки ТОЛЬКО конкретного товара (не весь образ)
TRYON_SINGLE_ITEM = """Virtual clothing try-on task for a SINGLE ITEM:

IMAGE 1 (MAIN): The customer's photo - this is the BASE image.
IMAGE 2+ (REFERENCE): Product photos showing the {category} item on a model or mannequin.

CRITICAL INSTRUCTIONS - EXTRACT AND APPLY ONLY THE CLOTHING ITEM:

STEP 1 - EXTRACT FROM REFERENCE:
- Look at Image 2+ and identify ONLY the {category} item (e.g., jacket, coat, blazer)
- Extract ONLY this single clothing piece from the reference images
- IGNORE everything else in the reference: the model, background, other clothing items, accessories
- Focus on the fabric, color, texture, cut, and style of JUST this {category} item

STEP 2 - PRESERVE FROM MAIN IMAGE (Image 1):
- Keep the EXACT person from Image 1 (face, body, pose, skin tone, hair)
- Keep the EXACT background from Image 1 - do NOT mix or blend backgrounds
- Keep ALL other clothing items the person is wearing (pants, shoes, shirt, etc.) - only replace the {category} item
- Keep the EXACT lighting, shadows, and color temperature from Image 1
- Keep the EXACT photo style and quality from Image 1

STEP 3 - APPLY THE ITEM:
- Place ONLY the extracted {category} item onto the person from Image 1
- The item should fit naturally on their body, matching their pose and proportions
- Maintain realistic fabric behavior: folds, draping, fit, and natural movement
- Ensure seamless integration: no visible seams, artifacts, or blending issues
- The item should look like it was photographed in the same environment as Image 1

ABSOLUTE PROHIBITIONS:
- DO NOT copy the background from reference images - use ONLY Image 1 background
- DO NOT copy the model from reference images - use ONLY the person from Image 1
- DO NOT change other clothing items - only replace the {category} item
- DO NOT blend or mix elements from different images
- DO NOT distort or modify the person's body, face, or pose
- DO NOT add elements that weren't in the original Image 1

RESULT: The person from Image 1, in their original background, wearing the {category} item from the reference, with all their other original clothing unchanged."""

# Промпт для примерки ВСЕГО образа (вся одежда модели)
TRYON_FULL_OUTFIT = """
Virtual clothing try-on task:

MAIN IMAGE = Image 1: the person trying on clothes (the customer).
REFERENCE OTHER IMAGES = Image 2: the full outfit to try on.

IMPORTANT! KEEP FROM THE MAIN IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The lighting and color scheme
- The photo quality and style

CHANGE ONLY THE CLOTHING:
- Put the full outfit from the reference images onto THE PERSON FROM THE MAIN IMAGE
- Replace all clothing on the person with the outfit from Image 2
- The outfit should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The outfit should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the main image!)
- The pose and body position
- The person's physical features

Result: same person, same background, wearing the full outfit from the reference.
"""