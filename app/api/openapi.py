from flask import jsonify
from app.api.schemas import (
    InvoiceSchema,
    ProductSchema,
    ReturnOrderSchema,
    SaleSchema,
    SupplierSchema,
    WarehouseSchema,
)
from app.api.schemas.purchase_order import PurchaseOrderSchema, PurchaseOrderItemSchema


def get_openapi_spec(api_version='v1'):
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Inventory API Platform',
            'version': api_version,
            'description': 'Enterprise-ready API foundation for inventory management.',
        },
        'servers': [
            {'url': '/api', 'description': 'API root'},
            {'url': f'/api/{api_version}', 'description': 'Versioned API root'},
        ],
        'paths': {
            '/api/v1/auth/login': {
                'post': {
                    'summary': 'Obtain JWT access and refresh tokens.',
                    'tags': ['Authentication'],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'username': {'type': 'string'},
                                        'password': {'type': 'string'},
                                    },
                                    'required': ['username', 'password'],
                                }
                            }
                        },
                    },
                    'responses': {
                        '200': {
                            'description': 'Token pair returned.',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'status': {'type': 'string'},
                                            'message': {'type': 'string'},
                                            'data': {
                                                'type': 'object',
                                                'properties': {
                                                    'access_token': {'type': 'string'},
                                                    'refresh_token': {'type': 'string'},
                                                    'user': {
                                                        'type': 'object',
                                                        'properties': {
                                                            'id': {'type': 'integer'},
                                                            'username': {'type': 'string'},
                                                            'email': {'type': 'string'},
                                                            'role': {'type': 'string'},
                                                        },
                                                    },
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        },
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/auth/refresh': {
                'post': {
                    'summary': 'Exchange a refresh token for a new access token.',
                    'tags': ['Authentication'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {
                            'description': 'New access token returned.',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'status': {'type': 'string'},
                                            'message': {'type': 'string'},
                                            'data': {'type': 'object', 'properties': {'access_token': {'type': 'string'}}},
                                        },
                                    }
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/auth/logout': {
                'post': {
                    'summary': 'Revoke an existing access token.',
                    'tags': ['Authentication'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {'$ref': '#/components/responses/Success'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/auth/me': {
                'get': {
                    'summary': 'Get current authenticated user profile.',
                    'tags': ['Authentication'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {
                            'description': 'User profile returned.',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'status': {'type': 'string'},
                                            'message': {'type': 'string'},
                                            'data': {
                                                'type': 'object',
                                                'properties': {
                                                    'id': {'type': 'integer'},
                                                    'username': {'type': 'string'},
                                                    'email': {'type': 'string'},
                                                    'role': {'type': 'string'},
                                                    'created_at': {'type': 'string', 'format': 'date-time'},
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/ping': {
                'get': {
                    'summary': 'API connectivity check endpoint.',
                    'tags': ['System'],
                    'responses': {
                        '200': {
                            'description': 'Ping successful.',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'status': {'type': 'string'},
                                            'message': {'type': 'string'},
                                            'data': {'type': 'object', 'properties': {'api_version': {'type': 'string'}, 'message': {'type': 'string'}}},
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            },
            '/api/v1/products': {
                'get': {
                    'summary': 'List products with paging, filtering, and search.',
                    'tags': ['Products'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Filter criteria as JSON or comma-separated key:value pairs.'},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {
                            'description': 'List of products.',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        '$ref': '#/components/schemas/ApiSuccessResponse'
                                    }
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Create a new product.',
                    'tags': ['Products'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Product'}
                            }
                        }
                    },
                    'responses': {
                        '201': {
                            'description': 'Product created successfully.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/products/{product_id}': {
                'parameters': [
                    {'name': 'product_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                ],
                'get': {
                    'summary': 'Get a single product by ID.',
                    'tags': ['Products'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {
                            'description': 'Product details returned.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'put': {
                    'summary': 'Update an existing product.',
                    'tags': ['Products'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Product'}
                            }
                        }
                    },
                    'responses': {
                        '200': {
                            'description': 'Product updated successfully.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'delete': {
                    'summary': 'Delete a product by ID.',
                    'tags': ['Products'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {
                            'description': 'Product deleted successfully.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/inventory': {
                'get': {
                    'summary': 'Retrieve warehouse stock levels.',
                    'tags': ['Inventory'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                        {'name': 'start_date', 'in': 'query', 'schema': {'type': 'string', 'format': 'date-time'}, 'description': 'Begin date filter for inventory levels.'},
                        {'name': 'end_date', 'in': 'query', 'schema': {'type': 'string', 'format': 'date-time'}, 'description': 'End date filter for inventory levels.'},
                    ],
                    'responses': {
                        '200': {
                            'description': 'Inventory levels returned.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/inventory/movements': {
                'get': {
                    'summary': 'Retrieve stock movement history.',
                    'tags': ['Inventory'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                        {'name': 'start_date', 'in': 'query', 'schema': {'type': 'string', 'format': 'date-time'}, 'description': 'Begin date filter for movements.'},
                        {'name': 'end_date', 'in': 'query', 'schema': {'type': 'string', 'format': 'date-time'}, 'description': 'End date filter for movements.'},
                    ],
                    'responses': {
                        '200': {
                            'description': 'Stock movements returned.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/inventory/low-stock': {
                'get': {
                    'summary': 'Retrieve low stock items across warehouses.',
                    'tags': ['Inventory'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {
                            'description': 'Low stock items returned.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/inventory/valuation': {
                'get': {
                    'summary': 'Retrieve inventory valuation details.',
                    'tags': ['Inventory'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                        {'name': 'start_date', 'in': 'query', 'schema': {'type': 'string', 'format': 'date-time'}, 'description': 'Begin date filter for inventory valuation.'},
                        {'name': 'end_date', 'in': 'query', 'schema': {'type': 'string', 'format': 'date-time'}, 'description': 'End date filter for inventory valuation.'},
                    ],
                    'responses': {
                        '200': {
                            'description': 'Inventory valuation returned.',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                }
            },
            '/api/v1/warehouses': {
                'get': {
                    'summary': 'Retrieve all warehouses.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Warehouses returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Create a new warehouse.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Warehouse'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Warehouse created successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/warehouses/{warehouse_id}': {
                'get': {
                    'summary': 'Retrieve a warehouse by ID.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [{'name': 'warehouse_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                    'responses': {
                        '200': {'description': 'Warehouse returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'put': {
                    'summary': 'Update a warehouse by ID.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [{'name': 'warehouse_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Warehouse'}
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Warehouse updated successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'delete': {
                    'summary': 'Delete a warehouse by ID.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [{'name': 'warehouse_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                    'responses': {
                        '200': {'description': 'Warehouse deleted successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/warehouses/{warehouse_id}/inventory': {
                'get': {
                    'summary': 'Retrieve stock balances for a warehouse.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'warehouse_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Warehouse inventory returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/warehouses/{warehouse_id}/movements': {
                'get': {
                    'summary': 'Retrieve stock transfer history for a warehouse.',
                    'tags': ['Warehouses'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'warehouse_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Warehouse transfer movements returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/suppliers': {
                'get': {
                    'summary': 'Retrieve all suppliers.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Suppliers returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Create a new supplier.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Supplier'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Supplier created successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/suppliers/{supplier_id}': {
                'get': {
                    'summary': 'Retrieve a supplier by ID.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [{'name': 'supplier_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                    'responses': {
                        '200': {'description': 'Supplier returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'put': {
                    'summary': 'Update a supplier by ID.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [{'name': 'supplier_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Supplier'}
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Supplier updated successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'delete': {
                    'summary': 'Delete a supplier by ID.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [{'name': 'supplier_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                    'responses': {
                        '200': {'description': 'Supplier deleted successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/suppliers/{supplier_id}/products': {
                'get': {
                    'summary': 'Retrieve products for a supplier.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'supplier_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Supplier products returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/suppliers/{supplier_id}/purchase-orders': {
                'get': {
                    'summary': 'Retrieve purchase orders for a supplier.',
                    'tags': ['Suppliers'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'supplier_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Supplier purchase orders returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/purchase-orders': {
                'get': {
                    'summary': 'List purchase orders with filters, sorting, and pagination.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Purchase orders returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Create a new purchase order.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/PurchaseOrder'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Purchase order created successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/purchase-orders/{purchase_order_id}': {
                'parameters': [
                    {'name': 'purchase_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                ],
                'get': {
                    'summary': 'Retrieve a single purchase order by ID.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {'description': 'Purchase order returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'put': {
                    'summary': 'Update a purchase order by ID.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/PurchaseOrder'}
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Purchase order updated successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
                'delete': {
                    'summary': 'Delete a purchase order by ID.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {'description': 'Purchase order deleted successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/purchase-orders/{purchase_order_id}/approve': {
                'post': {
                    'summary': 'Approve a pending purchase order.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'purchase_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'responses': {
                        '200': {'description': 'Purchase order approved successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/purchase-orders/{purchase_order_id}/receive': {
                'post': {
                    'summary': 'Receive inventory for a purchase order.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'purchase_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'items': {
                                            'type': 'array',
                                            'items': {
                                                'type': 'object',
                                                'properties': {
                                                    'item_id': {'type': 'integer'},
                                                    'quantity_received': {'type': 'integer'},
                                                },
                                                'required': ['item_id', 'quantity_received'],
                                            },
                                        }
                                    },
                                    'required': ['items'],
                                }
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Purchase order received successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/purchase-orders/{purchase_order_id}/cancel': {
                'post': {
                    'summary': 'Cancel a draft or pending purchase order.',
                    'tags': ['Purchase Orders'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'purchase_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'reason': {'type': 'string'},
                                    },
                                    'required': ['reason'],
                                }
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Purchase order cancelled successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/sales': {
                'get': {
                    'summary': 'List sales with filters, sorting, and pagination.',
                    'tags': ['Sales'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Sales returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Create a new sale.',
                    'tags': ['Sales'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'product_id': {'type': 'integer'},
                                        'quantity': {'type': 'integer'},
                                        'selling_price': {'type': 'number'},
                                        'customer_id': {'type': 'integer'},
                                        'destination_details': {'type': 'string'},
                                    },
                                    'required': ['product_id', 'quantity', 'selling_price'],
                                }
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Sale created successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/sales/{sale_id}': {
                'parameters': [
                    {'name': 'sale_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                ],
                'get': {
                    'summary': 'Retrieve a single sale by ID.',
                    'tags': ['Sales'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {'description': 'Sale returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/invoices': {
                'get': {
                    'summary': 'List invoices with filters, sorting, and pagination.',
                    'tags': ['Invoices'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Invoices returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Create a new invoice.',
                    'tags': ['Invoices'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Invoice'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Invoice created successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/invoices/{invoice_id}': {
                'parameters': [
                    {'name': 'invoice_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                ],
                'get': {
                    'summary': 'Retrieve a single invoice by ID.',
                    'tags': ['Invoices'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {'description': 'Invoice returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/invoices/{invoice_id}/payment': {
                'post': {
                    'summary': 'Record a payment for an invoice.',
                    'tags': ['Invoices'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'invoice_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'amount': {'type': 'number'},
                                        'method': {'type': 'string'},
                                        'reference': {'type': 'string'},
                                    },
                                    'required': ['amount', 'method'],
                                }
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Payment recorded successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/invoices/{invoice_id}/cancel': {
                'post': {
                    'summary': 'Cancel an invoice.',
                    'tags': ['Invoices'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'invoice_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'requestBody': {
                        'required': False,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'reason': {'type': 'string'},
                                    },
                                }
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Invoice cancelled successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/returns': {
                'get': {
                    'summary': 'List return orders with filters, sorting, and pagination.',
                    'tags': ['Returns'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1}},
                        {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                        {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_by', 'in': 'query', 'schema': {'type': 'string'}},
                        {'name': 'sort_order', 'in': 'query', 'schema': {'type': 'string', 'enum': ['asc', 'desc']}},
                    ],
                    'responses': {
                        '200': {'description': 'Return orders returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
                'post': {
                    'summary': 'Request a new return order.',
                    'tags': ['Returns'],
                    'security': [{'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ReturnOrder'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Return order requested successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                    },
                },
            },
            '/api/v1/returns/{return_order_id}': {
                'parameters': [
                    {'name': 'return_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                ],
                'get': {
                    'summary': 'Retrieve a single return order by ID.',
                    'tags': ['Returns'],
                    'security': [{'BearerAuth': []}],
                    'responses': {
                        '200': {'description': 'Return order returned.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            '/api/v1/returns/{return_order_id}/approve': {
                'post': {
                    'summary': 'Approve a return order.',
                    'tags': ['Returns'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'return_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'responses': {
                        '200': {'description': 'Return order approved successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/returns/{return_order_id}/reject': {
                'post': {
                    'summary': 'Reject a return order.',
                    'tags': ['Returns'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'return_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'reason': {'type': 'string'},
                                    },
                                    'required': ['reason'],
                                }
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Return order rejected successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '403': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
            '/api/v1/returns/{return_order_id}/cancel': {
                'post': {
                    'summary': 'Cancel a pending return order.',
                    'tags': ['Returns'],
                    'security': [{'BearerAuth': []}],
                    'parameters': [
                        {'name': 'return_order_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    ],
                    'requestBody': {
                        'required': False,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'reason': {'type': 'string'},
                                    },
                                }
                            }
                        }
                    },
                    'responses': {
                        '200': {'description': 'Return order cancelled successfully.', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiSuccessResponse'}}}},
                        '400': {'$ref': '#/components/responses/BadRequest'},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                }
            },
        },
        'components': {
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                }
            },
            'responses': {
                'BadRequest': {
                    'description': 'Bad request response.',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': '#/components/schemas/ErrorResponse'
                            }
                        }
                    }
                },
                'Unauthorized': {
                    'description': 'Authentication failed or missing credentials.',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': '#/components/schemas/ErrorResponse'
                            }
                        }
                    }
                },
                'NotFound': {
                    'description': 'Resource not found.',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': '#/components/schemas/ErrorResponse'
                            }
                        }
                    }
                },
                'Success': {
                    'description': 'Successful operation.',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': '#/components/schemas/StandardResponse'
                            }
                        }
                    }
                },
            },
            'schemas': {
                'StandardResponse': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'message': {'type': 'string'},
                        'data': {'type': 'object'},
                    },
                },
                'ApiSuccessResponse': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'data': {'type': 'object'},
                        'message': {'type': 'string'},
                        'meta': {'type': 'object'},
                    },
                },
                'ApiErrorResponse': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'error': {
                            'type': 'object',
                            'properties': {
                                'message': {'type': 'string'},
                                'code': {'type': 'string'},
                                'details': {'type': 'object'},
                            },
                        },
                    },
                },
                'ErrorResponse': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'message': {'type': 'string'},
                        'error_code': {'type': 'string'},
                        'errors': {'type': 'object'},
                    },
                },
                'Product': ProductSchema.to_openapi_schema(),
                'Warehouse': WarehouseSchema.to_openapi_schema(),
                'Supplier': SupplierSchema.to_openapi_schema(),
                'PurchaseOrder': PurchaseOrderSchema.to_openapi_schema(),
                'PurchaseOrderItem': PurchaseOrderItemSchema.to_openapi_schema(),
                'Invoice': InvoiceSchema.to_openapi_schema(),
                'Sale': SaleSchema.to_openapi_schema(),
            },
        },
    }

    return jsonify(spec)
