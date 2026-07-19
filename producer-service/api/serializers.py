from rest_framework import serializers

class ProductEventSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=['ProductCreated', 'ProductUpdated', 'ProductDeleted'])
    product_id = serializers.CharField(max_length=255)
    payload = serializers.DictField()
    
    def validate(self, data):
        event_type = data.get('event_type')
        payload = data.get('payload')
        
        if event_type == 'ProductCreated':
            required_fields = ['name', 'description', 'price', 'stock']
            for field in required_fields:
                if field not in payload:
                    raise serializers.ValidationError(f"'{field}' is required in payload for ProductCreated")
        elif event_type == 'ProductUpdated':
            if not payload:
                raise serializers.ValidationError("payload cannot be empty for ProductUpdated")
                
        return data
