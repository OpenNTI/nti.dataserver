PRMIA CUSTOMER RECEIPT
Date ${today}

Transaction ID: ${transaction_id}


Billed to:
${billed_to}
${nti_context.charge.Address}

%for item in nti_context.purchase.Order.Items:
${item.Quantity}x ${item.purchasable.Title} - ${format_currency_attribute(item.purchasable, 'Amount')} each

%endfor

Subtotal: ${format_currency_attribute(nti_context.purchase.Pricing, 'TotalNonDiscountedPrice')}
## XXX: JAM: Not sure how to figure out the discounts. I'm just deriving them...
%for item in nti_context.purchase.Pricing.Items:
%if item.Coupon and item.NonDiscountedPrice and item.PurchasePrice != item.NonDiscountedPrice:
Discount($item.Coupon): -${format_currency(item.NonDiscountedPrice - item.PurchasePrice, nti_context.purchase.Pricing.Currency)}
%endif
%endfor

ORDER TOTAL: ${format_currency_attribute(nti_context.charge, 'Amount')}


Payment Received: ${format_currency_attribute(nti_context.charge, 'Amount')}
${today} (**** **** **** ${nti_context.charge.CardLast4})
all sales are final


Thank you for your order, ${informal_username}! Your Items are available at ${request.application_url}


Please keep a copy of this receipt for your records.
If you have any questions, feel free to contact accounting@prmia.org
